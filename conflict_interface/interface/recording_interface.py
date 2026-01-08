import sys
from copy import deepcopy
from time import sleep
from time import time
from typing import Any, Callable, Optional

from cloudscraper25 import CloudScraper

from conflict_interface.data_types.authentication import AuthDetails
from conflict_interface.data_types.custom_types import HashMap
from conflict_interface.data_types.custom_types import LinkedList
from conflict_interface.data_types.game_api_types.game_state_action import GameStateAction
from conflict_interface.data_types.game_object_json import dump_any
from conflict_interface.game_api import GameApi
from conflict_interface.logger_config import get_logger


logger = get_logger()


class RecordingInterface:
    """
    Lightweight game interface that records raw game update responses.
    Does not parse game states and assumes a guest join.
    """

    def __init_callbacks(self):
        self._request_response_cb: Optional[Callable[[dict, dict, float], None]] = None
        self._update_cb: Optional[Callable[[float], None]] = None

    def __init__(self, game_id: int,
                 session: CloudScraper,
                 auth_details: AuthDetails,
                 proxy: dict | None = None):
        self.game_id = game_id
        self.game_api: GameApi = GameApi(session, auth_details, game_id, proxy=proxy)
        self.state_ids, self.time_stamps = HashMap(), HashMap()
        self.__init_callbacks()

    def set_proxy(self, proxy: dict):
        self.game_api.set_proxy(proxy)

    def unset_proxy(self):
        self.game_api.unset_proxy()

    def update(self) -> dict:
        """
        Request a game update and return the raw JSON response.
        """
        start = time()
        response = self._request_game_state(send_state_ids=True)
        elapsed_ms = (time() - start) * 1000.0
        if self._update_cb:
            try:
                self._update_cb(elapsed_ms)
            except Exception:
                pass
        return response

    def _request_game_state(self, send_state_ids: bool) -> dict:
        state_ids, time_stamps = (None, None)
        include_state_meta = False

        if send_state_ids and self.state_ids and self.time_stamps:
            state_ids = deepcopy(self.state_ids)
            time_stamps = deepcopy(self.time_stamps)
            include_state_meta = True

        action = GameStateAction(
            state_type=0,
            state_id="0",
            add_state_ids_on_sent=include_state_meta,
            option=None,
            state_ids=state_ids,
            time_stamps=time_stamps,
            actions=LinkedList()
        )

        payload = dump_any(action)
        response = self.game_api.make_game_server_request(payload)
        self._extract_state_metadata(response)
        return response


    def _extract_state_metadata(self, response) -> bool:
        """
        Extract state IDs and timestamps from the last raw response
        to enable incremental updates without parsing a GameState.
        """
        if not response:
            return False

        result = response.get("result")
        if not isinstance(result, dict):
            return False

        states = result.get("states")
        if not isinstance(states, dict):
            return False


        for state in states.values():
            if not isinstance(state, dict):
                continue
            state_type_raw = state.get("stateType")
            try:
                state_type = int(state_type_raw)
            except (TypeError, ValueError):
                continue

            state_id = state.get("stateID")
            if state_id is not None:
                self.state_ids[state_type] = str(state_id)

            time_stamp = state.get("timeStamp")
            if time_stamp is not None:
                try:
                    self.time_stamps[state_type] = int(time_stamp)
                except (TypeError, ValueError):
                    continue

        if len(self.state_ids) == 0 or len(self.time_stamps) == 0:
            return False

        return True

    def get_api(self) -> GameApi:
        return self.game_api
