from __future__ import annotations

import gc
from pathlib import Path
from time import sleep
from time import time
from typing import Optional

from pympler import asizeof

from conflict_interface.data_types.custom_types import HashMap
from conflict_interface.interface import HubInterface
from conflict_interface.interface import RecordingInterface
from tools.server_observer.static_map_cache import StaticMapCache
from tools.server_observer.account import Account
from tools.server_observer.storage import RecordingStorage

from tools.server_observer.recorder_logger import get_logger

logger = get_logger()


class ObservationSession:
    """
    Per-game observer that records server responses until game end.

    It patches the game API to persist responses via RecordingStorage and
    optionally saves game states. Static map data is cached once per map_id
    to avoid duplicate downloads during the session.
    """

    def __init__(
        self,
        config: dict,
        account: Optional[Account],
        map_cache: StaticMapCache,
    ):
        self.config = config
        self.account = account
        self.map_cache = map_cache
        self.hub_itf: Optional[HubInterface] = None
        self.game_itf: Optional[RecordingInterface] = None
        self.storage: Optional[RecordingStorage] = None
        self.game_id = config.get("game_id")
        self.update_interval: float = float(config.get("update_interval", 60.0))
        self.save_game_states: bool = False
        self.max_updates = config.get("max_updates")
        self.max_duration = config.get("max_duration")
        self.fat_session = False

    def _setup_storage(self):
        output_dir = self.config.get("output_dir", "./recordings")
        recording_name = self.config.get("recording_name") or f"game_{self.game_id}"
        output_path = Path(output_dir) / recording_name
        self.storage = RecordingStorage(str(output_path), self.save_game_states)
        self.storage.setup_logging()
        logger.info(f"ServerObserver storage initialized at {output_path}")

    def _get_hub_interface(self) -> Optional[HubInterface]:
        if self.account:
            return self.account.get_interface()

        username = self.config.get("username")
        password = self.config.get("password")
        proxy_url = self.config.get("proxy_url")
        if not username or not password:
            logger.error("Username and password are required when no account pool is provided")
            return None
        hub_itf = HubInterface()
        if proxy_url:
            hub_itf.set_proxy({"http": proxy_url, "https": proxy_url})
        hub_itf.login(username, password)
        return hub_itf

    def _on_request_response(self, request_payload: dict, response: dict, elapsed_ms: float):
        ts = time()
        self.storage.save_request_response(ts, request_payload or {}, response)
        if asizeof.asizeof(response) >= 1024 * 300:
            self.fat_session = True

        self.storage.update_resume_metadata({
            "time_stamps": self.game_itf.time_stamps,
            "state_ids": self.game_itf.state_ids,
        })

    def _prepare(self) -> bool:
        self.hub_itf = self._get_hub_interface()
        if not self.hub_itf:
            return False
        self.game_itf = RecordingInterface(
            game_id=self.game_id,
            session=self.hub_itf.api.session,
            auth_details=self.hub_itf.api.auth,
            proxy=self.hub_itf.api.proxy
        )
        self.game_itf.game_api.load_game_site()
        self.game_itf.set_request_response_callback(self._on_request_response)

        if self.storage.get_resume_metadata():
            self.game_itf.time_stamps = HashMap(self.storage.resume_metadata.get("time_stamps", {}))
            self.game_itf.state_ids = HashMap(self.storage.resume_metadata.get("state_ids", {}))
            game_state = self.game_itf._request_game_state(send_state_ids=True)
        else:
            game_state = self.game_itf._request_game_state(send_state_ids=False)
            map_id = int(game_state.get("result").get("states").get("3").get("map").get("mapID"))
            # Check if static map data is available locally
            if not self.map_cache.is_cached(map_id):
                logger.info(f"Downloading static map data for map_id {map_id}")
                static_map_data = self.game_itf.game_api.get_static_map_data()
                self.map_cache.save(map_id, static_map_data)
        gc.collect()

        return True

    def _observe_until_end(self) -> bool:
        updates_done = 0
        start_time = time()
        while True:
            logger.info(f"Sending update {updates_done} for game {self.game_id}")
            state = self.game_itf.update()
            updates_done += 1
            if self._is_game_ended(state):
                logger.info(f"Game {self.game_id} ended, stopping observation.")
                return True
            if self.max_updates is not None and updates_done >= self.max_updates:
                logger.info("Reached configured maximum number of updates, stopping observation.")
                return True
            if self.max_duration is not None and (time() - start_time) >= self.max_duration:
                logger.info("Reached configured maximum observation duration, stopping.")
                return True
            del state
            gc.collect()
            if self.fat_session:
                logger.info(f"Restarting session {self.game_id} due to large response size.")
                return True
            sleep(self.update_interval)

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
        try:
            self._setup_storage()
            if not self._prepare():
                return False

            return self._observe_until_end()
        except Exception as exc:
            logger.error(f"Observation for game {self.game_id} failed: {exc}")
            return False
        finally:
            # Clean up to free memory
            if self.storage:
                self.storage.teardown_logging()
            if self.game_itf:
                self.game_itf = None
            if self.hub_itf:
                self.hub_itf = None
            self.storage = None
