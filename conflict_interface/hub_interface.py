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
from conflict_interface.data_types.hub_game_info import HubGameInfo
from conflict_interface.game_api import GameAPI
from conflict_interface.game_interface import GameInterface
from conflict_interface.utils.exceptions import ConflictWebAPIError


def protected(func):
    def wrapper(self, *args, **kwargs):
        if self.auth:
            return func(self, *args, **kwargs)
    return wrapper


def parse_international_games(data):
    res = {}
    print(data)
    for item in data:
        properties = item["properties"]
        game = parse_dataclass(HubGameInfo, properties, None)
        game = cast(HubGameInfo, game)
        res[game.game_id] = game
    return res


class HubInterface:
    def __init__(self):
        self.session = Session()
        self.user_agent = UserAgent(platforms='desktop').random
        self.session.headers = {
                "User-Agent": self.user_agent,
                "Accept-Language": 'en-US,en;q=0.9',
        }
        self.auth = None

    def login(self, username, password):
        params = {
            'source': 'browser-desktop',
        }

        data = {
            'user': username,
            'pass': password,
        }

        response = self.session.post(
            'https://www.conflictnations.com/index.php',
            params=params,
            data=data,
        )
        response.raise_for_status()

        response_html = html.fromstring(response.text)

        url = response_html.xpath(r'//iframe[@id="ifm"]/@src')[0]

        self.auth = AuthDetails.from_url_parameters(url)

        self.auth.session_token = self.get_session_token()
        logging.debug("Login successful with username %s", username)

    @protected
    def send_api_request(self, params, action):
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        }

        keycode = "uberCon"

        if keycode != "open":
            params['authTstamp'] = self.auth.auth_tstamp
            params['authUserID'] = self.auth.user_id

        encoded_params = ""
        param_list = []
        if params:
            for key, value in params.items():
                param_list.append(key + "=" + str(value))
            encoded_params = "&".join(param_list)

        encoded_params_b64 = base64.b64encode(encoded_params.encode()).decode()
        data_string = "data=" + encoded_params_b64

        if keycode == "open":
            hash_prepare = keycode + action + encoded_params
        else:
            hash_prepare = keycode + action + encoded_params
            hash_prepare += self.auth.uber_auth_hash
        hash_str = hashlib.sha1(hash_prepare.encode()).hexdigest()

        params = {
            'eID': 'api',
            'key': keycode,
            'action': action,
            'hash': hash_str,
            'outputFormat': 'json',
            'apiVersion': '20141208',
        }
        response = self.session.post(
            'https://www.conflictnations.com/index.php',
            params=params,
            headers=headers,
            data=data_string,
        )
        response.raise_for_status()

        result = json.loads(response.text)
        if not (result["resultCode"] == 0 and result["resultMessage"] == "ok"):
            raise ConflictWebAPIError(result)

        return result["result"]

    def get_my_games(self, archived=False) -> dict[int, HubGameInfo]:
        params = {
                "userID": self.auth.user_id,
        }
        if archived:
            params["mygamesMode"] = "archived"

        res = self.send_api_request(params, "getInternationalGames")
        return parse_international_games(res)

    def get_global_games(self, **filters) -> dict[int, HubGameInfo] :
        last_page = False
        page = 0
        games = {}
        while not last_page:
            res = self.send_api_request({"userID": self.auth.user_id,
                                         "global": "1",
                                         "page": str(page)},
                                        "getInternationalGames")
            last_page = res["lastPage"]
            page += 1
            page_games = parse_international_games(res["games"])
            for page_game_id, page_game in page_games.items():
                if all([getattr(page_game, key) == val for key, val in filters.items()]):
                    games[page_game_id] = page_game
        return games

    def request_join_game(self, game_id: int):
        res = self.send_api_request({
            "userID": self.auth.user_id,
            "gameID": game_id,
            "password": ""
        }, "joinGame")
        return res

    def join_game(self, game_id: int, guest=False) -> GameInterface:
        if not self.is_in_game(game_id) and not guest:
            self.request_join_game(game_id)

        game_api = GameAPI(self.session.cookies.get_dict(),
                           self.session.headers,
                           deepcopy(self.auth),
                           game_id)
        game_interface = GameInterface(game_id, game_api)
        game_interface.join_game(guest)
        return game_interface

    def is_in_game(self, game_id: int) -> bool:
        return self.get_my_games(archived=False).get(game_id) is not None

    def get_session_token(self):
        res = self.send_api_request({
            "userID": self.auth.user_id,
        }, "getSessionToken")
        return res["sessionToken"]

