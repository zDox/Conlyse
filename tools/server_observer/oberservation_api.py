import gc
import re
from collections import defaultdict
from copy import deepcopy
from dataclasses import dataclass
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from hashlib import sha1
from json import dumps
from time import time

import httpx
from httpx import HTTPTransport

from conflict_interface.data_types.authentication import AuthDetails
from conflict_interface.data_types.custom_types import HashMap
from conflict_interface.data_types.custom_types import LinkedList
from conflict_interface.data_types.game_api_types.game_state_action import GameStateAction
from conflict_interface.data_types.game_object_json import dump_any
from tools.server_observer.recorder_logger import get_logger
from conflict_interface.utils.helper import unix_to_datetime

logger = get_logger()
SUPPORTED_CLIENT_VERSION = 207

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


class ObservationApi:
    def __init__(self,
                 transport: HTTPTransport,
                 headers: dict,
                 cookies: dict,
                 auth_details: AuthDetails,
                 game_id: int,
                 game_server_address: str,
                 client_version: int = SUPPORTED_CLIENT_VERSION,
                 proxy: dict = None):
        self.client = httpx.Client(transport=transport,
                                   headers=headers,
                                   cookies=cookies,
                                   proxy=proxy.get("http"),
                                   timeout=httpx.Timeout(
                                       connect=10.0,  # seconds to establish connection
                                       read=60.0,  # seconds to wait for a server response
                                       write=30.0,
                                       pool=5.0
                                   ))
        self.game_id = game_id
        self.player_id = 0
        self.auth = auth_details
        self.device_details = DeviceDetails.from_user_agent(headers.get("User-Agent"))
        self.request_id = 0
        self.client_version = client_version
        self.game_server_address = game_server_address
        self.map_id = None
        self.last_update_time = None
        self.server_time_offset = None
        if proxy:
            self.proxy = proxy
        else:
            self.proxy = defaultdict()

    def set_proxy(self, proxy: dict):
        self.proxy = proxy

    def unset_proxy(self):
        self.proxy = defaultdict()

    def make_game_server_request(self, parameters):
        headers = {
            'Accept': 'text/plain, */*; q=0.01',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            "Accept-Encoding": "gzip, deflate, br"
        }

        hash_hex = sha1(("undefined" + str(int(time() * 1000)))
                        .encode()).hexdigest()

        payload = {
            "requestID": self.request_id,
            "language": "en",
            **parameters,
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
            "lastCallDuration": 0,
        }
        logger.info(f"Sending Game API request {self.request_id} with params: {dumps(parameters)}")
        self.request_id += 1
        response = self.client.post(self.game_server_address,
                                         headers=headers,
                                        content=dumps(payload))
        response.raise_for_status()
        response_json = response.json()
        response.close()
        del response

        if not type(response_json["result"]) is int:
            if "timeStamp" in response_json["result"]:
                self.update_server_time(response_json["result"]["timeStamp"])
        else:
            self.update_server_time(0)

        if "result" in response_json and type(response_json["result"]) is dict:
            if response_json["result"].get("@c") == "ultshared.UltAuthentificationException":
                raise Exception(f"Authentfication failed while sending parameters {dumps(payload, indent=2)} to game server.")
        gc.collect()
        return response_json

    def client_time(self, time_scale) -> datetime:
        """
        Calculates the client time

        :param time_scale: The time_scale of the game
        """
        current_time = datetime.now(UTC)
        if not time_scale in (0.25, 1, 0.1):
            raise ValueError(f"Time scale cannot be {time_scale}. Must be 0.1, 0.25 or 1")
        if time_scale != 1:
            time_elapsed = timedelta(seconds = (current_time -self.last_update_time).total_seconds() / time_scale)
            return self.last_update_time + self.server_time_offset + time_elapsed
        return current_time + self.server_time_offset

    def update_server_time(self, t_stamp_now):
        self.last_update_time = datetime.now(UTC)

        t_stamp_now = int(t_stamp_now)
        if t_stamp_now == 0:
            seconds_since_epoch = (self.last_update_time - datetime(1970, 1, 1, tzinfo=UTC)).total_seconds()
            self.server_time_offset = timedelta(seconds = -seconds_since_epoch)
            return

        t_stamp_now = unix_to_datetime(t_stamp_now)
        self.server_time_offset = t_stamp_now - self.last_update_time


    def get_static_map_data(self):
        headers = {
            'Accept': 'application/json, text/javascript, */*; q=0.01',
        }

        params = {
            # 'bust': '1700054640135',
        }

        domain = "static1.bytro.com"
        url = f"https://{domain}/fileadmin/mapjson/live/{self.map_id}.json"
        response = self.client.get(
            url,
            params=params,
            headers=headers,
        )

        response.raise_for_status()
        return response.json()

    def request_game_state(self, state_ids: dict, time_stamps: dict) -> tuple[dict, dict, dict]:
        if state_ids and time_stamps:
            include_state_meta = True
            state_ids = HashMap(state_ids)
            time_stamps = HashMap(time_stamps)
        else:
            include_state_meta = False
            state_ids = HashMap()
            time_stamps = HashMap()

        logger.info(f"Requesting game state with {len(state_ids) if state_ids is not None else 'None'} state IDs and {len(time_stamps) if time_stamps is not None else 'None'} timestamps, including state meta: {include_state_meta}")

        action = GameStateAction(
            state_type=0,
            state_id="0",
            add_state_ids_on_sent=include_state_meta,
            option=None,
            state_ids=state_ids if include_state_meta else None,
            time_stamps=time_stamps if include_state_meta else None,
            actions=LinkedList()
        )

        payload = dump_any(action)
        response = self.make_game_server_request(payload)
        extraction_result = self._extract_state_metadata(response, state_ids, time_stamps)
        if not extraction_result:
            raise Exception(f"Game state extraction failed for {response}")
        return response, state_ids, time_stamps


    def _extract_state_metadata(self, response, state_ids, time_stamps) -> bool:
        """
        Extract state IDs and timestamps from the last raw response
        to enable incremental updates without parsing a GameState.
        """
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
                state_ids[state_type] = str(state_id)

            time_stamp = state.get("timeStamp")
            if time_stamp is not None:
                try:
                    time_stamps[state_type] = int(time_stamp)
                except (TypeError, ValueError):
                    continue

        if len(state_ids) == 0 or len(time_stamps) == 0:
            return False

        return True
