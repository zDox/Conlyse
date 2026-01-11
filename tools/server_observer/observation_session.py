from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import field
from time import sleep
from time import time
from typing import Optional

import httpx
from httpx import HTTPTransport
from pympler import asizeof

from conflict_interface.data_types.authentication import AuthDetails
from conflict_interface.game_api import GameApi
from conflict_interface.utils.exceptions import AuthenticationException
from tools.server_observer.account import Account
from tools.server_observer.observation_api import ObservationApi
from tools.server_observer.recorder_logger import get_logger
from tools.server_observer.static_map_cache import StaticMapCache
from tools.server_observer.storage import RecordingStorage

logger = get_logger()

MAX_RETRIES = 3
TIME_TILL_RETRY = 10

@dataclass
class ObservationPackage:
    game_id: int = None
    headers: dict = None
    cookies: dict = None
    proxy: dict = None
    auth: AuthDetails = None
    client_version: int = None
    game_server_address: str = None

    time_stamps: dict = field(default_factory=dict)
    state_ids: dict = field(default_factory=dict)

class ObservationSession:
    """
    Holds per-game session context (cookies, headers, proxy, auth) and schedules updates.
    Spawns short-lived ObservationWorker instances to perform individual update requests.
    """

    def __init__(
        self,
            game_id: int,
            account: Account,
            map_cache: StaticMapCache,
        ):
        self.account = account
        self.map_cache = map_cache
        self.game_id = game_id

        self.storage_path: str = f"./recordings/game_{self.game_id}"
        self.package = None

        self._start_time: Optional[float] = None
        self._updates_done = 0
        self.next_update_at: float = time()

    def reset(self):
        self.package = None
        storage = RecordingStorage(self.storage_path)
        storage.update_resume_metadata({})

    def needs_update(self, now: float) -> bool:
        return now >= self.next_update_at

    def create_worker(self) -> ObservationWorker:
        return ObservationWorker(self.account, self.game_id, self.package, self.map_cache)

    def update_package(self, other: ObservationPackage):
        self.package = other


class ObservationWorker:
    """
    Lightweight worker that performs a single update using the owning ObservationSession.
    """

    def __init__(self, account: Account, game_id: int, package: ObservationPackage = None, map_cache: StaticMapCache = None):
        self.account = account
        self.game_id = game_id
        self.storage = RecordingStorage(f"./recordings/game_{self.game_id}")
        self.storage.setup_logging()
        self.package: ObservationPackage = package
        self.map_cache = map_cache
        self.recording_itf = None


    def _on_request_response(self, response: dict):
        self.storage.save_response(response)
        if asizeof.asizeof(response) >= 1024 * 300:
            logger.warning(f"Large response size detected for game {self.game_id} ({asizeof.asizeof(response) / 1024} KB)")
        del response
        self.storage.update_resume_metadata(asdict(self.package))

    def ensure_observation_package(self) -> bool:
        if self.package is not None:
            return True
        resume_metadata = self.storage.get_resume_metadata()
        if resume_metadata and "auth" in resume_metadata:
            logger.info(f"Resuming from Storage for game {self.game_id}")
            auth = AuthDetails(**resume_metadata.pop("auth"))
            resume_metadata["auth"] = auth
            self.package = ObservationPackage(**resume_metadata)
            return True

        logger.info(f"Observation package not yet created, building package for game {self.game_id}")
        self.package = self.create_observation_package()
        return True

    def create_observation_package(self) -> ObservationPackage:
        hub_itf = self.account.get_interface()
        if hub_itf is None:
            return None
        game_api = GameApi(
            session=hub_itf.api.session,
            proxy=hub_itf.api.proxy,
            game_id=self.game_id,
            auth_details=hub_itf.api.auth
        )
        game_api.load_game_site()
        return ObservationPackage(
            game_id=game_api.game_id,
            headers=deepcopy(dict(game_api.session.headers)),
            cookies=deepcopy(dict(game_api.session.cookies)),
            proxy=deepcopy(dict(game_api.session.proxies)),
            auth=deepcopy(game_api.auth),
            client_version=game_api.client_version,
            game_server_address=game_api.game_server_address,
        )

    def reset_package(self):
        self.account.reset_interface()
        self.package = self.create_observation_package()

    def ensure_static_map_data(self, observation_api: ObservationApi, map_id: int) -> bool:
        if self.map_cache.is_cached(map_id):
            return True
        static_map_data = observation_api.get_static_map_data()
        self.map_cache.save(map_id, static_map_data)
        return True

    @staticmethod
    def _is_game_ended(response: Optional[dict]) -> bool:
        if not isinstance(response, dict):
            return False
        result = response.get("result")
        if not isinstance(result, dict):
            return False
        states = result.get("states", {})
        if not isinstance(states, dict):
            return False
        for state in states.values():
            if isinstance(state, dict) and state.get("gameEnded"):
                return True
        return False

    def run(self) -> bool:
        attempt = 1
        while True:
            logger.info(f"Starting update for game {self.game_id}")
            self.ensure_observation_package()
            observation_api = ObservationApi(
                HTTPTransport(),
                headers=self.package.headers,
                cookies=self.package.cookies,
                proxy=self.package.proxy,
                auth_details=self.package.auth,
                game_id=self.game_id,
                game_server_address=self.package.game_server_address,
            )
            try:
                game_state, self.package.state_ids, self.package.time_stamps = observation_api.request_game_state(
                    self.package.state_ids,
                    self.package.time_stamps,
                )
                self._on_request_response(game_state)
                if "result" in game_state and "states" in game_state["result"] and "3" in game_state["result"]["states"] and "map" in game_state["result"]["states"]["3"]:
                    map_id = int(game_state.get("result").get("states").get("3").get("map").get("mapID"))
                    self.ensure_static_map_data(observation_api, map_id)
                if self._is_game_ended(response=game_state):
                    return False
                return True
            except AuthenticationException:
                if attempt >= MAX_RETRIES:
                    return False
                logger.info(f"Authentication failed, resetting package and retrying...")
                attempt += 1
                self.reset_package()
                continue
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 401:
                    logger.info(f"Authentication failed, resetting package and retrying...")
                    attempt += 1
                    self.reset_package()
                    continue
                elif e.response.status_code >= 500:
                    logger.warning(f"GameServer returned HTTP {e.response.status_code}, retrying in {TIME_TILL_RETRY} seconds...")
                    sleep(TIME_TILL_RETRY)
                    continue
            except httpx.NetworkError or httpx.ReadTimeout:
                logger.info(f"GameServer is not responding, retrying in {TIME_TILL_RETRY} seconds...")
                sleep(TIME_TILL_RETRY)
                continue
        return False