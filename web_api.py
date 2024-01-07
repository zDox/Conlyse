import requests
import lxml.html
import json
import base64
import hashlib
from parser import parse_international_games
from exceptions import ConflictWebAPIError
from fake_useragent import UserAgent
from pprint import pprint
from data_types import GameInfo

interesting_keys = ["userID", "authHash", "authTstamp", "chatAuth",
                    "chatAuthTstamp", "uberAuthHash",
                    "uberAuthTstamp", "rights"]


class WebAPI():
    def __init__(self):
        self.session = requests.Session()
        self.user_agent = UserAgent().random
        self.session.headers = {
                "User-Agent": self.user_agent,
                "Accept-Language": 'en-US,en;q=0.9',
        }

    def login(self, username, password):
        headers = {
        }

        params = {
            'id': '322',
            'source': 'browser-desktop',
        }

        data = {
            'user': username,
            'pass': password,
        }

        response = self.session.post(
            'https://www.conflictnations.com/index.php',
            params=params,
            headers=headers,
            data=data,
        )
        response.raise_for_status()

        response_html = lxml.html.fromstring(response.text)

        url = response_html.xpath(r'//iframe[@id="ifm"]/@src')[0]
        parameters = url.split("&")

        self.auth = {}
        for parameter in parameters[1:]:
            key, value = parameter.split("=")
            if key not in interesting_keys:
                continue
            self.auth[key] = value

    def sendApiRequest(self, params, action):
        headers = {
            'Host': 'www.conflictnations.com',
            'Sec-Ch-Ua': '"Chromium";v="119", "Not?A_Brand";v="24"',
            'Accept': '*/*',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'X-Requested-With': 'XMLHttpRequest',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"Linux"',
            'Origin': 'https://www.conflictnations.com',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Dest': 'empty',
        }

        keycode = "uberCon"

        if keycode != "open":
            params['authTstamp'] = self.auth["authTstamp"]
            params['authUserID'] = self.auth["userID"]

        encoded_params = ""
        param_list = []
        if params:
            for key, value in params.items():
                param_list.append(key + "=" + value)
            encoded_params = "&".join(param_list)

        encoded_params_b64 = base64.b64encode(encoded_params.encode()).decode()
        data_string = "data=" + encoded_params_b64

        if keycode == "open":
            hash_prepare = keycode + action + encoded_params
        else:
            hash_prepare = keycode + action + encoded_params
            hash_prepare += self.auth["uberAuthHash"]
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

    def get_my_games(self):
        res = self.sendApiRequest({"userID": self.auth["userID"]},
                                  "getInternationalGames")
        pprint(res)
        return parse_international_games(res)

    def get_global_games(self):
        last_page = False
        page = 0
        games = []
        while not last_page:
            res = self.sendApiRequest({"userID": self.auth["userID"],
                                       "global": "1",
                                       "page": str(page)},
                                      "getInternationalGames")
            last_page = res["lastPage"]
            page += 1
            games = games + parse_international_games(res["games"])
        return games

    def join_game(self, game_info: GameInfo):
        pass
