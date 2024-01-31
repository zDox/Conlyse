from data_types.authentification import AuthDetails
from exceptions import ConflictJoinError
from data_types.states import States
from data_types.static_map_data import StaticMapData

from requests import Session
from hashlib import sha1
from lxml import html
import re
from dataclasses import dataclass
from json import loads, dumps
from time import time


@dataclass
class DeviceDetails:
    os: str
    device: str

    @staticmethod
    def from_user_agent(user_agent):
        os = re.findall(r"(?<=\()([A-Z])\w+(?=;| )", user_agent)[0]
        return DeviceDetails(os, "")


class GameAPI:
    def __init__(self, cookies: dict, headers: dict, auth_details: AuthDetails,
                 game_id: int):
        self.session = Session()
        self.game_id = game_id
        self.player_id = 0
        self.auth = auth_details
        self.device_details = DeviceDetails.from_user_agent(
                headers["User-Agent"])
        self.request_id = 1

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
                "lastCallDuration": 0,
                "version": self.client_version,
                "tstamp": str(self.auth.auth_tstamp),
                "client": "con-client",
                "hash": hash_hex,
                "sessionTstamp": 0,
                "gameID": str(self.game_id),
                "playerID": self.player_id,
                "siteUserID": str(self.auth.user_id),
                "adminLevel": None,
                "rights": self.auth.rights,
                "userAuth": self.auth.auth,
        }

        self.request_id += 1

        if actions:
            data["actions"] = ["java.util.LinkedList", [actions]]

        response = self.session.post(self.game_server_address,
                                     headers=headers,
                                     data=dumps(data))
        response.raise_for_status()
        return loads(response.text)

    def request_first_game_activation(self, guest):
        res = self.make_game_server_request({
            "@c": "ultshared.action.UltActivateGameAction",
            "selectedPlayerID": -1,
            "selectedTeamID": -1,
            "randomTeamAndCountrySelection": False,
            "os": self.device_details.os,
            "device": self.device_details.device,
            }, None)
        if not guest:
            self.player_id = res["result"]
            return self.player_id
        return 0

    def request_selected_country(self, country_id=-1, team_id=-1,
                                 random_team_country_selection=False):
        res = self.make_game_server_request({
            "@c": "ultshared.action.UltActivateGameAction",
            "selectedPlayerID": country_id,
            "selectedTeamID": team_id,
            "randomTeamAndCountrySelection": random_team_country_selection,
            "device": self.device_details.device,
            "os": self.device_details.os,
            }, None)
        self.player_id = res["result"]
        return self.player_id

    def request_login_action(self):
        res = self.make_game_server_request(
                {
                    "@c": "ultshared.action.UltUpdateGameStateAction",
                    "stateType": 0,
                    "stateID": "0",
                    "addStateIDsOnSent": True,
                    "option": None,
                },
                {
                    "requestID": "actionReq-1",
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
                }
            )
        return States.from_dict(res["result"]["states"])

    def request_game_update(self, with_states=True) -> States:

        if with_states:
            time_stamps = self.time_stamps
            state_ids = self.state_ids

        res = self.make_game_server_request(
                {
                    "@c": "ultshared.action.UltUpdateGameStateAction",
                    "stateType": 0,
                    "stateID": "0",
                    "addStateIDsOnSent": True,
                    "option": None,
                    "stateIDs": state_ids,
                    "tstamps": time_stamps,
                })

        # Set stateIDs and tstamps from response
        for state in list(res["result"]["states"].values())[1:]:
            state_type = str(state["stateType"])

            self.time_stamps[state_type] = state["timeStamp"]
            self.state_ids[state_type] = state["stateID"]

        return States.from_dict(res["result"]["states"])
