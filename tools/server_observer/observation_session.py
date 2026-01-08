from __future__ import annotations

import gc
from pathlib import Path
from time import time
from typing import Optional

from httpx import HTTPTransport
from pympler import asizeof

from conflict_interface.data_types.custom_types import HashMap
from conflict_interface.interface import HubInterface
from conflict_interface.interface import RecordingInterface
from tools.server_observer.account import Account
from tools.server_observer.oberservation_api import ObservationApi
from tools.server_observer.recorder_logger import get_logger
from tools.server_observer.static_map_cache import StaticMapCache
from tools.server_observer.storage import RecordingStorage

logger = get_logger()


class ObservationSession:
    """
    Holds per-game session context (cookies, headers, proxy, auth) and schedules updates.
    Spawns short-lived ObservationWorker instances to perform individual update requests.
    """

    def __init__(
        self,
        config: dict,
        account: Optional[Account],
        map_cache: StaticMapCache,
        transport: HTTPTransport,
    ):
        self.config = config
        self.account = account
        self.map_cache = map_cache
        self.transport = transport
        self.game_id = config.get("game_id")
        self.update_interval: float = float(config.get("update_interval", 60.0))
        self.save_game_states: bool = False
        self.max_updates = config.get("max_updates")
        self.max_duration = config.get("max_duration")
        self.scenario_id = config.get("scenario_id")

        self.hub_itf: Optional[HubInterface] = None
        self.storage: Optional[RecordingStorage] = None

        # captured connection data
        self.headers = None
        self.cookies = None
        self.proxy = None
        self.auth = None
        self.client_version = None
        self.game_server_address = None

        self.fat_session = False
        self._prepared = False
        self._start_time: Optional[float] = None
        self._updates_done = 0
        self.next_update_at: float = time()

    def _setup_storage(self):
        if self.storage:
            return
        output_dir = self.config.get("output_dir", "./recordings")
        recording_name = self.config.get("recording_name") or f"game_{self.game_id}"
        output_path = Path(output_dir) / recording_name
        self.storage = RecordingStorage(str(output_path), self.save_game_states)
        self.storage.setup_logging()

    def _get_hub_interface(self) -> Optional[HubInterface]:
        if self.account:
            return self.account.get_interface()
        raise Exception("No account provided")

    def _capture_connection_details(self, game_itf: RecordingInterface):
        self.headers = dict(game_itf.game_api.session.headers)
        self.cookies = dict(game_itf.game_api.session.cookies)
        self.proxy = self.hub_itf.api.proxy if self.hub_itf else None
        self.auth = game_itf.game_api.auth
        self.client_version = game_itf.game_api.client_version
        self.game_server_address = game_itf.game_api.game_server_address

    def _prepare_interfaces(self) -> Optional[RecordingInterface]:
        self.hub_itf = self._get_hub_interface()
        if not self.hub_itf:
            return None
        game_itf = RecordingInterface(
            game_id=self.game_id,
            session=self.hub_itf.api.session,
            auth_details=self.hub_itf.api.auth,
        )
        game_itf.game_api.load_game_site()
        self._capture_connection_details(game_itf)
        return game_itf

    def _attach_observation_api(self, game_itf: RecordingInterface):
        game_itf.game_api = ObservationApi(
            self.transport,
            self.headers,
            self.cookies,
            self.auth,
            self.game_id,
            self.game_server_address,
            self.client_version,
            self.proxy,
        )

    def _on_request_response(self, game_itf: RecordingInterface, request_payload: dict, response: dict, elapsed_ms: float):
        ts = time()
        self.storage.save_request_response(ts, request_payload, response)
        if asizeof.asizeof(response) >= 1024 * 300:
            logger.warning(f"Large response size detected for game {self.game_id} ({asizeof.asizeof(response)} bytes)")
            self.fat_session = True

        self.storage.update_resume_metadata({
            "time_stamps": game_itf.time_stamps,
            "state_ids": game_itf.state_ids,
        })
        del response

    def _prepare(self) -> bool:
        self._setup_storage()
        game_itf = self._prepare_interfaces()
        if not game_itf:
            return False
        self._attach_observation_api(game_itf)

        if self.storage.get_resume_metadata() and False:
            game_itf.time_stamps = HashMap(self.storage.resume_metadata.get("time_stamps", {}))
            game_itf.state_ids = HashMap(self.storage.resume_metadata.get("state_ids", {}))
            game_state = game_itf._request_game_state(send_state_ids=True)
            self._on_request_response(game_itf, {}, game_state, 0.0)
        else:
            game_state = game_itf._request_game_state(send_state_ids=False)
            self._on_request_response(game_itf, {}, game_state, 0.0)
            map_id = int(game_state.get("result").get("states").get("3").get("map").get("mapID"))
            if not self.map_cache.is_cached(map_id):
                logger.info(f"Downloading static map data for map_id {map_id}")
                static_map_data = game_itf.game_api.get_static_map_data()
                self.map_cache.save(map_id, static_map_data)
            del game_state
        gc.collect()
        game_itf = None
        return True

    def ensure_prepared(self) -> bool:
        if self._prepared:
            return True
        if not self._prepare():
            return False
        self._prepared = True
        self._start_time = time()
        self.next_update_at = self._start_time
        return True

    def needs_update(self, now: float) -> bool:
        return now >= self.next_update_at

    def perform_update(self) -> bool:
        if not self.ensure_prepared():
            return False
        worker = self.create_worker()
        if worker is None:
            return False
        return worker.run()

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

    def close(self):
        if self.storage:
            self.storage.teardown_logging()
        if self.game_itf:
            self.game_itf = None
        if self.hub_itf:
            self.hub_itf = None
        self.storage = None

    def create_worker(self) -> Optional["ObservationWorker"]:
        if not self.ensure_prepared():
            return None
        return ObservationWorker(self)


class ObservationWorker:
    """
    Lightweight worker that performs a single update using the owning ObservationSession.
    """

    def __init__(self, session: ObservationSession):
        self.session = session
        self.game_itf = RecordingInterface(
            game_id=session.game_id,
            session=session.hub_itf.api.session if session.hub_itf else None,
            auth_details=session.hub_itf.api.auth if session.hub_itf else None,
        )
        session._attach_observation_api(self.game_itf)

    def run(self) -> bool:
        sess = self.session
        logger.info(f"Sending update {sess._updates_done} for game {sess.game_id}")
        state = self.game_itf._request_game_state(True)
        sess._on_request_response(self.game_itf, {}, state, 0.0)
        sess._updates_done += 1
        if sess._is_game_ended(state):
            logger.info(f"Game {sess.game_id} ended, stopping observation.")
            return False
        if sess.max_updates is not None and sess._updates_done >= sess.max_updates:
            logger.info("Reached configured maximum number of updates, stopping observation.")
            return False
        if sess.max_duration is not None and (time() - sess._start_time) >= sess.max_duration:
            logger.info("Reached configured maximum observation duration, stopping.")
            return False
        del state
        gc.collect()
        if sess.fat_session:
            logger.info(f"Restarting session {sess.game_id} due to large response size.")
            return False
        sess.next_update_at = time() + sess.update_interval
        return True
