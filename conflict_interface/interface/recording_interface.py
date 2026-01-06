from copy import deepcopy
from typing import Any

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

    def __init__(self, game_id: int,
                 session: CloudScraper,
                 auth_details: AuthDetails,
                 proxy: dict | None = None):
        self.game_id = game_id
        self.game_api: GameApi = GameApi(session, auth_details, game_id, proxy=proxy)
        self.static_map_data: Any | None = None
        self.last_response: dict | None = None

    def set_proxy(self, proxy: dict):
        self.game_api.set_proxy(proxy)

    def unset_proxy(self):
        self.game_api.unset_proxy()

    def load_game(self) -> dict:
        """
        Join the game as guest, fetch static map data and perform an initial update.
        """
        self.game_api.load_game_site()
        self.static_map_data = self.game_api.get_static_map_data()
        return self._request_game_state(send_state_ids=False)

    def update(self) -> dict:
        """
        Request a game update and return the raw JSON response.
        """
        return self._request_game_state(send_state_ids=True)

    def _request_game_state(self, send_state_ids: bool) -> dict:
        state_ids, time_stamps = (None, None)
        include_state_meta = False

        if send_state_ids:
            state_ids, time_stamps = self._extract_state_metadata()
            include_state_meta = state_ids is not None and time_stamps is not None

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
        self.last_response = deepcopy(response)
        return response

    def _extract_state_metadata(self) -> tuple[HashMap | None, HashMap | None]:
        """
        Extract state IDs and timestamps from the last raw response
        to enable incremental updates without parsing a GameState.
        """
        if not self.last_response:
            return None, None

        result = self.last_response.get("result")
        if not isinstance(result, dict):
            return None, None

        states = result.get("states")
        if not isinstance(states, dict):
            return None, None

        state_ids: HashMap[int, str] = HashMap()
        time_stamps: HashMap[int, int] = HashMap()

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
                state_ids[state_type] = str(state_id)

            time_stamp = state.get("timeStamp")
            if time_stamp is not None:
                try:
                    time_stamps[state_type] = int(time_stamp)
                except (TypeError, ValueError):
                    continue

        if len(state_ids) == 0 or len(time_stamps) == 0:
            return None, None

        return state_ids, time_stamps

    def get_api(self) -> GameApi:
        return self.game_api
