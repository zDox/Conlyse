from __future__ import annotations

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
from typing import TYPE_CHECKING

from cloudscraper25 import CloudScraper
from lxml import html
from requests import Session

from conflict_interface.logger_config import get_logger
from conflict_interface.utils.exceptions import CountryUnselectedException
from conflict_interface.utils.exceptions import GameJoinException
from conflict_interface.utils.helper import unix_to_datetime

VERSION = 208 # TODO how to do this


if TYPE_CHECKING:
    from conflict_interface.api.authentication import AuthDetails

logger = get_logger()


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


class GameApi:
    @staticmethod
    def country_selected(func):
        """
        Decorator function to ensure a country is selected before executing the wrapped function.

        Only allows the execution of the wrapped function if `is_country_selected` returns True.
        If no country is selected, raises a CountryUnselectedException.

        Parameters:
            func (Callable): The function to be wrapped by the decorator.

        Returns:
            Callable: The wrapped function that enforces the country selection check.
        """

        @wraps(func)
        def wrap(self, *args, **kwargs):
            if self.is_country_selected():
                return func(self, *args, **kwargs)
            else:
                raise CountryUnselectedException("Country not selected.")

        return wrap

    def __init__(self, session: CloudScraper, auth_details: AuthDetails,
                 game_id: int, proxy: dict = None,):
        self.session = session
        self.game_id = game_id
        self.player_id = 0
        self.auth = auth_details
        self.device_details = DeviceDetails.from_user_agent(session.headers.get("User-Agent"))
        self.request_id = 0
        self.index_html_url = None
        self.client_version = None
        self.game_server_address = None
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
                                    params=params, headers=headers, proxies=self.proxy)

        response.raise_for_status()

        # Now need to get the gameserver address and map_id
        response_html = html.fromstring(response.text)

        url = response_html.xpath(r'//iframe[@id="ifm"]/@src')[0]
        del response_html
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
        response = self.session.get(self.index_html_url, headers=headers, proxies=self.proxy)

        response.raise_for_status()

        match = re.search(r'clientVersion=(\d+)', response.text)
        if match:
            self.client_version = int(match.group(1))
            if self.client_version != VERSION:
                logger.warning(f"Client version is {self.client_version} which is not the newest version by this library (supported {VERSION}).")
        else:
            raise GameJoinException(f"Could not find client_version \
                    in request {response.text}")

    def load_game_site(self):
        self.load_game_php()
        self.load_index_html()

    def make_game_server_request(self, parameters):
        headers = {
            'Accept': 'text/plain, */*; q=0.01',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            "Accept-Encoding": "gzip, deflate, br"
        }

        hash_hex = sha1(("undefined" + str(int(time() * 1000)))
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
            "playerID": self.player_id,
            "siteUserID": str(self.auth.user_id),
            "adminLevel": None,
            "rights": self.auth.rights,
            "userAuth": self.auth.auth,
            "lastCallDuration": 0,
        }
        logger.debug(f"Sending Game API request {self.request_id} with params: {dumps(parameters)}")
        self.request_id += 1
        with Session() as session:
            with session.post(self.game_server_address,
                                             headers=headers,
                                            cookies=self.session.cookies,
                                             data=dumps(data),
                                             proxies=self.proxy,
                                            stream=True) as response:

                response.raise_for_status()
                response_json = response.json()
            del response
        del session

        if not type(response_json["result"]) is int:
            if "timeStamp" in response_json["result"]:
                self.update_server_time(response_json["result"]["timeStamp"])
        else:
            self.update_server_time(0)

        if "result" in response_json and type(response_json["result"]) is dict:
            if response_json["result"].get("@c") == "ultshared.UltAuthentificationException":
                raise Exception(f"Authentfication failed while sending parameters {dumps(data, indent=2)} to game server.")
        gc.collect()
        return response_json

    def reset(self):
        print("Resetting session")
        new_scraper = CloudScraper.create_scraper(disableCloudflareV2=True, stealth_options={
            'min_delay': 0.01,
            'max_delay': 1,
            'human_like_delays': True,
            'randomize_headers': True,
            'browser_quirks': True
        })
        new_scraper.headers = self.session.headers
        new_scraper.proxies = self.session.proxies
        new_scraper.cookies = self.session.cookies
        self.session.close()
        del self.session
        self.session = new_scraper

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
        response = self.session.get(
            url,
            params=params,
            headers=headers,
            proxies=self.proxy
        )

        response.raise_for_status()
        return response.json()

    def get_image(self, path: str) -> bytes:
        response = self.session.get(
            "https://www.conflictnations.com/clients/con-client/con-client_live/images/warfare/" + path,
            proxies=self.proxy
        )

        response.raise_for_status()
        return response.content

    def get_sprite(self, path: str) -> str:
        response = self.session.get(
            "https://www.conflictnations.com/clients/con-client/con-client_live/images/sprites/" + path,
            proxies=self.proxy
        )

        response.raise_for_status()
        return response.content