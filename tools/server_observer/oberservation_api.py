import gc
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from functools import wraps
from hashlib import sha1
from json import dumps
from time import time

import httpx
from cloudscraper25 import CloudScraper
from httpx import HTTPTransport
from lxml import html
from requests import Session

from conflict_interface.data_types.authentication import AuthDetails
from conflict_interface.logger_config import get_logger
from conflict_interface.utils.exceptions import CountryUnselectedException
from conflict_interface.utils.exceptions import GameJoinException
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
        logger.debug(f"Sending Game API request {self.request_id} with params: {dumps(parameters)}")
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