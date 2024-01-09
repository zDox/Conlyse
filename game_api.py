from authentification import AuthDetails
from exceptions import ConflictJoinError

from requests import Session
from lxml import html
from pprint import pprint
import re


class GameAPI:
    def __init__(self, cookies: dict, headers: dict, auth_details: AuthDetails,
                 game_id: int):
        self.session = Session()
        self.game_id = game_id
        self.auth = auth_details

        self.game_server_address = None
        self.map_id = None

        # Set cookies from previous ConflictInterface Session
        for key, value in cookies.items():
            self.session.cookies.set(key, value)

        # Set headers from previous ConflictInterface Session
        self.session.headers = headers

    def load_game_php(self):
        """
        loads the game.php page to get the game_server_address and map_id
        """
        headers = {
            'Host': 'www.conflictnations.com',
            'Upgrade-Insecure-Requests': '1',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,\
                    image/avif,image/webp,image/apng,*/*;q=0.8,application/\
                    signed-exchange;v=b3;q=0.7',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-User': '?1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Ch-Ua': '"Chromium";v="119", "Not?A_Brand";v="24"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"Linux"',
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
                    self.game_server_address = value

                case "mapID":
                    self.map_id = value

    def load_index_html(self):
        """
        Loads the index.html file to get the client_version
        """
        if not self.index_html_url:
            raise AttributeError("index_html_url is not set")

        headers = {
            'Sec-Ch-Ua': '"Chromium";v="119", "Not?A_Brand";v="24"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"Linux"',
            'Upgrade-Insecure-Requests': '1',
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
            'Sec-Ch-Ua-Mobile': '?0',
        }

        params = {
            'bust': '1700054640135',
        }

        domain = "static1.bytro.com"
        url = f"https://{domain}/fileadmin/mapjson/live/{self.map_id}.json"
        response = self.session.get(
            url,
            params=params,
            headers=headers,
        )
