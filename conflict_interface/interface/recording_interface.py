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


    def get_api(self) -> GameApi:
        return self.game_api
