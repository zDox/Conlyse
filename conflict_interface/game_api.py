from requests import Session
from lxml import html

from collections.abc import MutableMapping
from hashlib import sha1
import re
from dataclasses import dataclass
from json import loads, dumps
from time import time

from .data_types import AuthDetails, States, StaticMapData
from .utils.exceptions import ConflictJoinError, GameActivationException, GameActivationErrorCodes


@dataclass
class DeviceDetails:
    os: str
    device: str

    @staticmethod
    def from_user_agent(user_agent):
        os = re.findall(r"\(([^;]+);", user_agent)
        if os:
            return DeviceDetails(os[0], "desktop")
        else:
            return DeviceDetails("Unknown", "")


class GameAPI:
    def __init__(self, cookies: dict, headers: MutableMapping, auth_details: AuthDetails,
                 game_id: int):
        self.session = Session()
        self.game_id = game_id
        self.player_id = 0
        self.auth = auth_details
        self.device_details = DeviceDetails.from_user_agent(
                headers["User-Agent"])
        self.request_id = 1
        self.action_request_id = 1

        self.game_server_address = None
        self.map_id = None

        # Set cookies from previous ConflictInterface Session
        for key, value in cookies.items():
            self.session.cookies.set(key, value)

        # Set headers from previous ConflictInterface Session
        self.session.headers = headers

        # Get set from the auto GameUpdate request
        self.time_stamps = {"@c": "java.util.HashMap"}
        self.state_ids = {"@c": "java.util.HashMap"}

    def load_game_php(self):
        """
        loads the game.php page to get the game_server_address and map_id
        """
        headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,\
                    image/avif,image/webp,image/apng,*/*;q=0.8,application/\
                    signed-exchange;v=b3;q=0.7',
        }

        params = {
            'bust': '1',
            'uid': str(self.auth.user_id),
            'gameID': str(self.game_id),
        }

        response = self.session.get('https://www.conflictnations.com/play.php',
                                    params=params, headers=headers)

        response.raise_for_status()

        # Now need to get the gameserver address and map_id
        response_html = html.fromstring(response.text)

        url = response_html.xpath(r'//iframe[@id="ifm"]/@src')[0]

        self.index_html_url = url

        parameters = url.split('&')
        for parameter in parameters[1:]:
            key, value = parameter.split("=")
            match key:
                case "gs":
                    self.game_server_address = f"https://{value}"
                case "mapID":
                    self.map_id = value
                case "auth":
                    self.auth.auth = value
                case "authTstamp":
                    self.auth.auth_tstamp = value

    def load_index_html(self):
        """
        Loads the index.html file to get the client_version
        """
        if not self.index_html_url:
            raise AttributeError("index_html_url is not set")

        headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,\
                    image/avif,image/webp,image/apng,*/*;q=0.8,application/\
                    signed-exchange;v=b3;q=0.7',
        }
        response = self.session.get(self.index_html_url, headers=headers)

        response.raise_for_status()


        match = re.search(r'clientVersion=(\d+)', response.text)
        if match:
            self.client_version = int(match.group(1))
        else:
            raise ConflictJoinError(f"Could not find client_version \
                    in request {response.text}")

    def load_game_site(self):
        self.load_game_php()
        self.load_index_html()

    def get_static_map_data(self):
        headers = {
            'Accept': 'application/json, text/javascript, */*; q=0.01',
        }

        params = {
            # 'bust': '1700054640135',
        }

        domain = "static1.bytro.com"
        url = f"https://{domain}/fileadmin/mapjson/live/{self.map_id}.json"
        response = self.session.get(
            url,
            params=params,
            headers=headers,
        )

        response.raise_for_status()
        return StaticMapData.from_dict(loads(response.text))

    def make_game_server_request(self, parameters, actions=None):
        headers = {
            'Accept': 'text/plain, */*; q=0.01',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        }

        hash_hex = sha1(("undefined" + str(int(time()*1000)))
                        .encode()).hexdigest()

        data = {
                "requestID": self.request_id,
                "language": "en",
                **parameters,
                "version": self.client_version,
                "tstamp": str(self.auth.auth_tstamp),
                "client": "con-client",
                "hash": hash_hex,
                "sessionTstamp": 0,
                "gameID": str(self.game_id),
                "playerID": str(self.player_id),
                "siteUserID": str(self.auth.user_id),
                "adminLevel": None,
                "rights": self.auth.rights,
                "userAuth": self.auth.auth,
        }

        self.request_id += 1

        if actions:
            data["actions"] = ["java.util.LinkedList", actions]

        response = self.session.post(self.game_server_address,
                                     headers=headers,
                                     data=dumps(data))
        response.raise_for_status()
        return loads(response.text)

    def request_game_activation(self, selected_player_id=0, selected_team_id=0, random_team_country_selection=False) -> int:
        res = self.make_game_server_request({
            "@c": "ultshared.action.UltActivateGameAction",
            "selectedPlayerID": selected_player_id,
            "selectedTeamID": selected_team_id,
            "randomTeamAndCountrySelection": random_team_country_selection,
            "os": self.device_details.os,
            "device": self.device_details.device,
            }, None)

        try:
            raise GameActivationException.from_error_code(res["result"])
        except ValueError:
            pass
        self.player_id = res["result"]
        return self.player_id


    def request_game_state_action(self, actions):
        return self.make_game_server_request({
            "@c": "ultshared.action.UltUpdateGameStateAction",
            "stateType": 0,
            "stateID": "0",
            "addStateIDsOnSent": True,
            "option": None,
            "stateIDs": self.state_ids,
            "tstamps": self.time_stamps,
            }, actions)

    def request_province_action(self, province_id, building_id):
        res = self.request_game_state_action([
            {"requestID": f"actionReq-{self.action_request_id}",
             "language": "en",
             "@c": "ultshared.action.UltUpdateProvinceAction",
             "provinceIDs": [
                 "java.util.Vector", [province_id]], "slot": 0, "mode": 1,
             "upgrade": {"@c": "mu", "c": 0, "cn": False, "e": False, "rp": None, "id": building_id, "pl": 0}}
        ])
        self.action_request_id =+ 1
        return res

    def request_login_action(self) -> States:
        res = self.request_game_state_action([
                {
                    "requestID": f"actionReq-{self.action_request_id}",
                    "language": "en",
                    "@c": "ultshared.action.UltLoginAction",
                    "resolution": "1920x1080",
                    "sysInfos": {
                        "@c": "ultshared.action.UltSystemInfos",
                        "verbose": False,
                        "clientVersion": self.client_version,
                        "processors": "",
                        "accMem": "",
                        "javaVersion": "",
                        "osArch": "",
                        "osName": "UNIX",
                        "osVersion": "",
                        "osPatchLevel": "",
                        "userCountry": "",
                        "screenWidth": 1920,
                        "screenHeight": 1080
                        }
                }])
        self.action_request_id =+ 1
        if "states" not in res["result"]:
            raise ConflictJoinError(f"Login failed with error code {res['result']}")
        return States.from_dict(res["result"]["states"])

    def request_game_update(self) -> States:
        res = self.make_game_server_request(
                {
                    "@c": "ultshared.action.UltUpdateGameStateAction",
                    "stateType": 0,
                    "stateID": "0",
                    "addStateIDsOnSent": True,
                    "option": None,
                    "stateIDs": self.state_ids,
                    "tstamps": self.time_stamps,
                })
        # Set stateIDs and tstamps from response
        for state in list(res["result"]["states"].values())[1:]:
            state_type = str(state["stateType"])

            self.time_stamps[state_type] = state["timeStamp"]
            self.state_ids[state_type] = state["stateID"]

        return States.from_dict(res["result"]["states"])
