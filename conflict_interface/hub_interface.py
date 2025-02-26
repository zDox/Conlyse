import logging
from copy import deepcopy
from typing import cast

from fake_useragent import UserAgent
from requests import Session
from lxml import html

import json
import base64
import hashlib

from conflict_interface.data_types.authentification import AuthDetails
from conflict_interface.data_types.game_object import parse_dataclass
from conflict_interface.data_types.hub_game import HubGame
from conflict_interface.game_api import GameAPI
from conflict_interface.game_interface import GameInterface
from conflict_interface.utils.exceptions import ConflictWebAPIError





class HubInterface:
    def __init__(self):
        self.session = Session()
        self.user_agent = UserAgent(platforms='desktop').random
        self.session.headers = {
                "User-Agent": self.user_agent,
                "Accept-Language": 'en-US,en;q=0.9',
        }
        self.auth = None

    def join_game(self, game_id: int, guest=False) -> GameInterface:
        if not self.is_in_game(game_id) and not guest:
            self.get_api().request_join_game(game_id)

        game_api = GameAPI(self.session.cookies.get_dict(),
                           self.session.headers,
                           deepcopy(self.auth),
                           game_id)
        game_interface = GameInterface(game_id, game_api)
        game_interface.join_game(guest)
        return game_interface






    def is_in_game(self, game_id: int) -> bool:
        return self.get_my_games(archived=False).get(game_id) is not None



