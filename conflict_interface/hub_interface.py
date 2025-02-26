from copy import deepcopy

from fake_useragent import UserAgent
from requests import Session

from conflict_interface.game_api import GameAPI
from conflict_interface.game_interface import GameInterface
from conflict_interface.hub_api import HubApi


class HubInterface:
    def __init__(self):
        self.api: HubApi = HubApi()

    def login(self, username, password):
        self.api.login(username, password)

    def logout(self):
        self.api.logout()

    def register(self, username, email, password):
        self.api.register_user(username, email, password)

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



