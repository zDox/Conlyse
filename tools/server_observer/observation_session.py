from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import field
from pathlib import Path
from time import sleep
from time import time
from typing import Optional

import httpx
from httpx import HTTPTransport

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
            storage_path: Path,
            metadata_path: Optional[Path] = None,
            long_term_storage_path: Optional[Path] = None,
            file_size_threshold: Optional[int] = None
        ):
        self.account = account
        self.map_cache = map_cache
        self.game_id = game_id

        self.storage_path = storage_path
        self.metadata_path = metadata_path
        self.long_term_storage_path = long_term_storage_path
        self.file_size_threshold = file_size_threshold
        self.package = None
        self._shared_transport: Optional[HTTPTransport] = None
        self._storage: Optional[RecordingStorage] = None

        self._start_time: Optional[float] = None
        self._updates_done = 0
        self.next_update_at: float = time()

    def reset(self):
        self.package = None
        self._shared_transport = None
        self._ensure_storage().update_resume_metadata({})

    def needs_update(self, now: float) -> bool:
        return now >= self.next_update_at
    
    def _ensure_storage(self) -> RecordingStorage:
        """Ensure storage instance is initialized and return it."""
        if self._storage is None:
            self._storage = RecordingStorage(
                self.storage_path, 
                metadata_path=self.metadata_path,
                long_term_storage_path=self.long_term_storage_path,
                file_size_threshold=self.file_size_threshold
            )
        return self._storage

    def create_worker(self) -> ObservationWorker:
        # Check if resume data exists to decide on transport reuse
        has_resume_data = self._ensure_storage().has_resume_metadata()
        
        # For sessions with resume data, reuse the transport to reduce overhead
        if has_resume_data:
            if self._shared_transport is None:
                self._shared_transport = HTTPTransport()
            transport = self._shared_transport
        else:
            # For first updates (no resume data), create a new transport
            # This isolates the large initial response in thread memory
            transport = None

        return ObservationWorker(
            self.account,
            self.storage_path,
            self.game_id, 
            self.package, 
            self.map_cache,
            transport=transport,
            metadata_path=self.metadata_path,
            long_term_storage_path=self.long_term_storage_path,
            file_size_threshold=self.file_size_threshold
        )

    def update_package(self, other: ObservationPackage):
        self.package = other


class ObservationWorker:
    """
    Lightweight worker that performs a single update using the owning ObservationSession.
    """

    def __init__(self,
                 account: Account,
                 storage_path: Path,
                 game_id: int,
                 package: ObservationPackage = None,
                 map_cache: StaticMapCache = None,
                 transport: Optional[HTTPTransport] = None,
                 metadata_path: Optional[Path] = None,
                 long_term_storage_path: Optional[Path] = None,
                 file_size_threshold: Optional[int] = None):
        self.account = account
        self.game_id = game_id
        self.storage = RecordingStorage(
            storage_path, 
            metadata_path=metadata_path,
            long_term_storage_path=long_term_storage_path,
            file_size_threshold=file_size_threshold
        )
        self.storage.setup_logging()
        self.package: ObservationPackage = package
        self.map_cache = map_cache
        self.recording_itf = None
        self._transport = transport

    def cleanup(self):
        """Clean up resources used by this worker."""
        if self.storage:
            self.storage.teardown_logging()
            self.storage = None

    def __enter__(self):
        """Support context manager protocol."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Ensure cleanup happens when exiting context."""
        self.cleanup()
        return False


    def _on_request_response(self, response: dict):
        self.storage.update_resume_metadata(asdict(self.package))
        self.storage.save_response(response)
        del response

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
            headers=dict(game_api.session.headers),
            cookies=dict(game_api.session.cookies),
            proxy=dict(game_api.session.proxies),
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

            with self._create_observation_api() as observation_api:
                try:
                    game_state = self._fetch_and_update_game_state(observation_api)
                    self._process_map_data(observation_api, game_state)

                    if self._is_game_ended(response=game_state):
                        return False

                    return True

                except AuthenticationException:
                    if not self._handle_auth_failure(attempt):
                        return False
                    attempt += 1

                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 401:
                        if not self._handle_auth_failure(attempt):
                            return False
                        attempt += 1
                    elif e.response.status_code >= 500:
                        self._handle_server_error(e.response.status_code)

                except (httpx.NetworkError, httpx.ReadTimeout):
                    self._handle_network_error()

    def _create_observation_api(self) -> ObservationApi:
        # Use provided transport (reused) or create a new one (first update)
        transport = self._transport or HTTPTransport()
        api = ObservationApi(
            transport,
            headers=self.package.headers,
            cookies=self.package.cookies,
            proxy=self.package.proxy,
            auth_details=self.package.auth,
            game_id=self.game_id,
            game_server_address=self.package.game_server_address,
        )

        return api

    def _fetch_and_update_game_state(self, observation_api: ObservationApi) -> dict:
        game_state, self.package.state_ids, self.package.time_stamps = (
            observation_api.request_game_state(
                self.package.state_ids,
                self.package.time_stamps,
            )
        )

        # Update auth and connection details - only deepcopy auth as it's a complex object
        # Cookies and headers are simple dicts that can be shallow copied
        self.package.auth = deepcopy(observation_api.auth)
        self.package.cookies = dict(observation_api.client.cookies)
        self.package.headers = dict(observation_api.client.headers)
        self.package.game_server_address = observation_api.game_server_address

        self._on_request_response(game_state)
        return game_state

    def _process_map_data(self, observation_api: ObservationApi, game_state: dict) -> None:
        try:
            map_id = (
                game_state.get("result", {})
                .get("states", {})
                .get("3", {})
                .get("map", {})
                .get("mapID")
            )

            if map_id is not None:
                self.ensure_static_map_data(observation_api, int(map_id))
        except (ValueError, TypeError):
            pass  # Map data not available or invalid

    def _handle_auth_failure(self, attempt: int) -> bool:
        if attempt >= MAX_RETRIES:
            return False

        logger.warning("Authentication failed, resetting package and retrying...")
        self.reset_package()
        return True

    def _handle_server_error(self, status_code: int) -> None:
        logger.warning(
            f"GameServer returned HTTP {status_code}, "
            f"retrying in {TIME_TILL_RETRY} seconds..."
        )
        sleep(TIME_TILL_RETRY)

    def _handle_network_error(self) -> None:
        logger.warning(
            f"GameServer is not responding, "
            f"retrying in {TIME_TILL_RETRY} seconds..."
        )
        sleep(TIME_TILL_RETRY)