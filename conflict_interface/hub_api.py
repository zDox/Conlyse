import base64
import hashlib
import json
from collections import defaultdict
from functools import wraps
from time import sleep
from typing import Any
from urllib.parse import urlencode

import lxml
from cloudscraper25 import CloudScraper
from fake_useragent import UserAgent
from lxml import html
from requests import Response

from conflict_interface.data_types.authentication import AuthDetails
from conflict_interface.data_types.hub_types.ajax_request import AjaxRequest
from conflict_interface.data_types.hub_types.hub_result_code import HubResultCode
from conflict_interface.data_types.hub_types.identification_text import EMAIL_IN_CONFLICT_OF_NATIONS_IN_USE_TEXT
from conflict_interface.data_types.hub_types.identification_text import INVALID_USER_OR_PASSWORD_TEXT
from conflict_interface.data_types.hub_types.identification_text import SUCCESSFUL_REGISTRATION_DETAILS_TEXT
from conflict_interface.data_types.hub_types.identification_text import TEMP_IP_REGISTRATION_BAN
from conflict_interface.logger_config import get_logger
from conflict_interface.utils.exceptions import AuthenticationException
from conflict_interface.utils.exceptions import AuthenticationFailed
from conflict_interface.utils.exceptions import GameFull
from conflict_interface.utils.exceptions import GameJoiningFailedOldGame
from conflict_interface.utils.exceptions import InvalidCountry
from conflict_interface.utils.exceptions import InvalidParameterValue
from conflict_interface.utils.exceptions import JoiningGameFailed
from conflict_interface.utils.exceptions import MaxJoinedGamesExceeded
from conflict_interface.utils.exceptions import MissingParameter
from conflict_interface.utils.exceptions import NotEnoughTickets
from conflict_interface.utils.exceptions import RestrictedAction
from conflict_interface.utils.exceptions import TooManyGameJoinsTooFrequently
from conflict_interface.utils.exceptions import TooManyMessage

logger = get_logger()

HUB_RESULT_CODE_EXCEPTION_MAPPING = {
    HubResultCode.AuthenticationFailed: AuthenticationFailed,
    HubResultCode.RestrictedAction: RestrictedAction,
    HubResultCode.MissingParameter: MissingParameter,
    HubResultCode.JoiningGameFailed: JoiningGameFailed,
    HubResultCode.GameFull: GameFull,
    HubResultCode.InvalidCountry: InvalidCountry,
    HubResultCode.InvalidParameterValue: InvalidParameterValue,
    HubResultCode.MaxJoinedGamesExceeded: MaxJoinedGamesExceeded,
    HubResultCode.TooManyMessage: TooManyMessage,
    HubResultCode.GameJoiningFailedOldGame: GameJoiningFailedOldGame,
    HubResultCode.TooManyGameJoinsTooFrequently: TooManyGameJoinsTooFrequently,
    HubResultCode.NotEnoughTickets: NotEnoughTickets,
}

SESSION_TOKEN_RETRIES = 3

def get_user_name_taken_response_text(username):
    return f'<script type="text/javascript">setNameCheckResponse(0, "Username already taken", 2, "{username}");</script>'

def protected(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        if self.auth:
            return func(self, *args, **kwargs)
        else:
            raise AuthenticationException("Trying to access protected method without authentication. Please login first.")
    return wrapper

class HubApi:
    DEFAULT_KEY_CODE = "uberCon"
    HOST = "https://www.conflictnations.com/"

    def __init__(self, proxy: dict = None):
        self.session = CloudScraper.create_scraper(disableCloudflareV2=True,
                                                   stealth_options={
                                                       'min_delay': 0.01,
                                                       'max_delay': 1,
                                                       'human_like_delays': True,
                                                       'randomize_headers': True,
                                                       'browser_quirks': True
                                                   }
                                                   )
        self.user_agent = UserAgent(platforms='desktop').random
        self.session.headers = {
                "User-Agent": self.user_agent,
                "Accept-Language": 'en-US,en;q=0.9',
        }
        self.auth = None

        if proxy:
            self.proxy = proxy
        else:
            self.proxy = defaultdict()

    def set_proxy(self, proxy: dict):
        self.proxy = proxy

    def unset_proxy(self):
        self.proxy = defaultdict()

    def set_certificate(self, file_path):
        self.session.verify = file_path

    def send_ajax_request(self, request: AjaxRequest) -> Response:
        """
        Sends an AJAX request based on the parameters defined in the given `AjaxRequest` object.

        This method builds a request URL using the provided object attributes, appends any necessary
        query parameters, and sends the request using the session's HTTP method.

        Raises a `NotImplementedError` if the `buffer_request` flag in the `AjaxRequest` is enabled,
        as this feature is not currently supported.

        Parameters:
            request (AjaxRequest): An instance of the AjaxRequest class containing all the
            necessary parameters and settings required to build and send the AJAX request.

        Returns:
            Response: The HTTP response object received from the server after making the
            request.

        Raises:
            NotImplementedError: When the `buffer_request` flag in the `AjaxRequest` is set to
            True, indicating a request to buffer responses, which is not implemented.
        """
        url = request.host + "/index.php"
        query_params = {
            "eID": "ajax",
            "action": request.action,
            "L": str(request.language_id),
            "ref": request.callback_obj_name,
            "req": request.name,
            "reqID": str(request.current_request),
        }

        if request.is_polling:
            query_params["poll"] = "1"
        if request.evaluate_response:
            query_params["eval_response"] = "1"

        body_data = {}
        for i in range(len(request.keys)):
            if request.keys[i] is not None and request.values[i] is not None:
                body_data[request.keys[i]] = str(request.values[i])

        if request.buffer_request:
            raise NotImplementedError("Buffer request not implemented yet")

        request.current_request += 1

        logger.debug(f"Sending AJAX request to {url}")
        response = self.session.request(method=request.method,
                                        url=url,
                                        params=query_params,
                                        data=body_data,
                                        proxies=self.proxy)
        return response

    @protected
    def send_api_request(self, params: dict, action: str, keycode: str = DEFAULT_KEY_CODE) -> Any:
        """
        Sends an API request to the Conflict Nations hub server.

        This method constructs and sends an API request based on the provided
        keycode, parameters, and action. It performs hashing for request
        authentication, encodes parameters in base64, and ensures the response
        validity according to the server's response codes.

        Parameters:
            params: Key-value pair of parameters to include in the API request.
            action: Specifies the action being performed by the request.
            keycode: API keycode used to identify the request type. Some keycodes require
                    additional authentication parameters.

        Raises:
            ConflictWebAPIError: Raised when the response returned by the API indicates a failure,
                based on the result code and message in the response.
            requests.exceptions.RequestException: Raised when there's an issue with the HTTP request such as
                connectivity problems.

        Returns:
            Any: Extracted result data from the API response after ensuring its validity.
        """
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        }

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
        logger.debug(f"Sending API request to {self.HOST} with params: {params}")

        response = self.session.post(
            'https://www.conflictnations.com/index.php',
            params=params,
            headers=headers,
            data=data_string,
            proxies=self.proxy,
        )
        response.raise_for_status()

        result = json.loads(response.text)
        try:
            result_code = HubResultCode(result["resultCode"])
        except ValueError:
            raise ValueError(f"Invalid hub result code: {result['resultCode']} message: {result['resultMessage']}")
        if result_code.OK:
            return result["result"]
        elif result_code in HUB_RESULT_CODE_EXCEPTION_MAPPING:
            raise HUB_RESULT_CODE_EXCEPTION_MAPPING.get(result_code)(result["resultMessage"])
        else:
            raise Exception(result["resultMessage"])


    def check_login(self, username: str, password: str) -> bool:
        """
        Checks whether the provided login credentials are valid.

        This method sends an AJAX request with the provided username and password
        to verify the login credentials. The response from the server is checked
        to confirm if the login attempt was successful or not.

        Args:
            username (str): The username to authenticate.
            password (str): The password associated with the username.

        Returns:
            bool: True if the login credentials are valid; False otherwise.
        """
        rm = AjaxRequest(
            name="object_name",
            host=self.HOST,
            callback_obj_name="object_name",
            action="loginPassword",
            language_id=0,
            keys=["titleID", "userName", "pwd"],
            values=['2000', username, password],
        )
        response = self.send_ajax_request(rm)
        if response.text.endswith(INVALID_USER_OR_PASSWORD_TEXT):
            return False
        else:
            return True

    def check_username_available(self, username: str) -> bool:
        """
        Checks if a given username is available.

        This method sends a request to check the availability of a username and returns
        a boolean indicating whether the username is taken. The method constructs an
        Ajax request object with specific keys and values, then sends the request and
        analyzes the response to determine availability.

        Parameters:
            username: The username to check for availability.

        Returns:
            bool: True if the username is available, False if it is already taken.
        """
        rm = AjaxRequest(
            name="object_name",
            host=self.HOST,
            callback_obj_name="object_name",
            action="name",
            language_id=0,
            keys=["titleID", "name", "Ip"],
            values=['2000', username, 110], # TODO Figure out why Ip has value 110
        )
        response = self.send_ajax_request(rm)
        if response.text.endswith(get_user_name_taken_response_text(username)):
            return False
        else:
            return True

    def check_email_available(self, email: str) -> bool:
        """
        Checks if the provided email address is available for use by verifying against
        predefined returned text patterns from a server response.

        The method sends an Ajax request to determine whether an email is available
        for use. Depending on the server's response, it returns a boolean indicating
        availability. If the email conflict text or supremacy conflict text is found
        in the response, the email is considered unavailable.

        Parameters:
            email: The email address to check for availability.

        Returns:
            bool: True if the email is available for use, False otherwise.
        """
        rm = AjaxRequest(
            name="object_name",
            host=self.HOST,
            callback_obj_name="object_name",
            action="email",
            language_id=0,
            keys=["titleID", "email"],
            values=['2000', email],
        )
        response = self.send_ajax_request(rm)
        if response.text.endswith(EMAIL_IN_CONFLICT_OF_NATIONS_IN_USE_TEXT):
            return False
        elif response.text.endswith(EMAIL_IN_CONFLICT_OF_NATIONS_IN_USE_TEXT):
            return False
        else:
            return True

    def check_registration_details(self, values: str) -> bool:
        """
        Checks the registration details by creating an AjaxRequest object with specific
        parameters and sending the AJAX request. It is unknown if it has a use case
        or effect on the serverside.

        Returns
        -------
        - The response from the AJAX request.

        Raises
        ------
        None
        """
        rm = AjaxRequest(
            name="object_name",
            host=self.HOST,
            callback_obj_name="object_name",
            action="registration_details",
            language_id=0,
            keys=["Ip", "Ipv", "titleID", "values", "submit_id"],
            values=["110", "1", "2000", values, "sg_reg_form_0"],
        )
        response = self.send_ajax_request(rm)
        if response.text.endswith(SUCCESSFUL_REGISTRATION_DETAILS_TEXT):
            return True
        else:
            logger.info("Registration details check failed. Got response: " + response.text)
            return False


    @staticmethod
    def check_temp_ip_ban(response_text: str) -> bool:
        return TEMP_IP_REGISTRATION_BAN in response_text

    def load_main_page(self) -> tuple[str, dict]:
        """
        Fetches and parses the main page to retrieve form action URL and form data.

        This method sends a GET request to the host's main page, extracts the
        form with ID 'sg_reg_form_0', and gathers its action URL and data. It uses
        lxml's HTML parsing capabilities to locate and parse the form.

        Returns:
            A tuple containing the action URL and a dictionary of the
            form data.

        Raises:
            HTTPError: If the GET request to the main page fails.
        """
        response = self.session.get(self.HOST, proxies=self.proxy)
        response.raise_for_status()
        parsed_html = lxml.html.fromstring(response.text)
        form = parsed_html.get_element_by_id("sg_reg_form_0")
        form_data = dict(form.form_values())
        logger.debug(f"Loaded main page action: {form.action} form data: {form_data}")
        return form.action, form_data

    def load_authentication_from_response(self, response: Response):
        """
        Parses the authentication details from an HTTP response and initializes the
        authentication attributes for the class instance. It identifies the
        authentication URL from an iframe within the HTML response body, validates its
        existence, and extracts required authentication information. It is used
        in the login and register methods to retrieve the authentication details.

        Args:
            response: The HTTP response object containing the details of
            the authentication iframe.

        Raises:
            Exception: If the authentication iframe with the required ID cannot be
            located within the response HTML. As we expect´the function to be only called,
            when the authentication was successful.
        """
        parsed_html = lxml.html.fromstring(response.text)

        iframe_src = parsed_html.xpath(r'//iframe[@id="ifm"]/@src')
        if len(iframe_src) != 1:
            raise Exception("Could not find authentication url")

        self.auth = AuthDetails.from_url_parameters(iframe_src[0])
        for i in range(SESSION_TOKEN_RETRIES):
            try:
                self.auth.session_token = self.get_session_token()
            except Exception as e:
                if i == SESSION_TOKEN_RETRIES -1:
                    raise e
                sleep_amount = 5 * (i +1)
                logger.debug(f"Sleeping for {sleep_amount} seconds")
                sleep(sleep_amount)

    def get_session_token(self) -> str:
        """
        Retrieves a session token for the current user.

        Returns
        -------
        - The session token retrieved from the API response.
        """
        res = self.send_api_request({
            "userID": self.auth.user_id,
        }, "getSessionToken")
        if "sessionToken" not in res:
            logger.debug(f"Could not retrieve session token. Response was {res}")
            raise AuthenticationException("Could not get session token")
        return res["sessionToken"]

    def register_user(self, username: str, email: str, password: str) -> bool:
        """
        Registers a new user by submitting the registration form data to the server.
        The process involves loading the main page to bypass the Cross-Site
        Request Forgery (CSRF) protection, validating username and email availability,
        and submitting the registration form with the provided details. Upon successful
        submission, the authentication data is loaded from the server response.

        Parameters:
            username: The desired username for registration.
            email: The email address to register with.
            password: The password for the new account.

        Returns:
            bool: True if registration and authentication are successful, otherwise False.

        Raises:
            None
        """
        username_ok = self.check_username_available(username)
        email_ok = self.check_email_available(email)
        if not username_ok:
            logger.info(f"Trying to register username {username} which is already taken")
            return False
        if not email_ok:
            logger.info(f"Trying to register with email {email} which is already taken")
            return False
        if len(username) >= 20:
            logger.info(f"Trying to register username {username} which is too long. Maximum are 20 characters.")
            return False

        """
        Registration needs to load the main page (conflictnations.com) as 
        the form is protected by a captcha and Cross-Site forgery protection. 
        Hence we need to load the main page in order to retrieve the token.
        """
        form_action, form_data = self.load_main_page()

        form_data["sg[reg][username]"] = username
        form_data["sg[reg][email]"] = email
        form_data["sg[reg][password]"] = password

        reg_details_res = self.check_registration_details(values=urlencode(form_data))
        if not reg_details_res:
            return False

        res = self.session.post(self.HOST+form_action, data=form_data, proxies=self.proxy)
        if HubApi.check_temp_ip_ban(res.text):
            logger.info("Temp IP ban detected, waiting 10 minutes")
            return False
        self.load_authentication_from_response(res)
        return True

    def login(self, username, password) -> bool:
        """
        Logs a user into the system by sending authentication data to the server. Verifies the credentials
        via self.check_login() and sends a POST request to authenticate. Updates the
        session with authentication details upon successful login.

        Parameters
        ----------
        username : The username of the user attempting to log in.
        password : The password of the user attempting to log in.

        Returns
        -------
        - Returns False self.check_login() fails otherwise returns True.

        Raises
        ------
        HTTPError
            Raised if the HTTP POST request to the server is unsuccessful.

        """
        if not self.check_login(username, password):
            return False

        params = {
            "source": "browser-desktop",
        }

        data = {
            'user': username,
            'pass': password,
        }

        response = self.session.post(self.HOST, params=params, data=data, proxies=self.proxy)

        response.raise_for_status()
        self.load_authentication_from_response(response)
        return True

    def logout(self):
        self.session = CloudScraper.create_scraper(disableCloudflareV2=True,
                                                   stealth_options = {
                                                       'min_delay': 0.01,
                                                       'max_delay': 1,
                                                       'human_like_delays': True,
                                                       'randomize_headers': True,
                                                       'browser_quirks': True
                                                   })
        self.user_agent = UserAgent(platforms='desktop').random
        self.session.headers = {
                "User-Agent": self.user_agent,
                "Accept-Language": 'en-US,en;q=0.9',
        }
        self.auth = None
        logger.debug("Logged out")

    """
    Functions where user has to be logged in.
    """


    @protected
    def get_my_games(self, archived: bool=False) -> list[Any]:
        """
        Fetches a list of games associated with the authenticated user, optionally
        retrieving archived games.

        Arguments:
            archived: Optional; whether to retrieve archived games. Defaults to False.

        Returns:
            The response from the API containing the requested games.

        Raises:
            Any errors raised during API request are passed through.
        """
        params = {
                "userID": self.auth.user_id,
        }
        if archived:
            params["mygamesMode"] = "archived"

        return self.send_api_request(params, "getInternationalGames")



    @protected
    def get_global_games(self) -> list[Any]:
        """
        Fetches the list of global games available for the authenticated user.

        This method retrieves all games using the API in a paginated manner, iterating
        through pages until the last page has been accessed. The resulting list of games
        is collected and returned to the caller.

        Returns:
            list[Any]: A list of games retrieved from the global scope. Each game in
            the list may have various data related to the game, as returned by the API.
        """
        last_page = False
        page = 0
        games = []
        while not last_page:
            res = self.send_api_request({"userID": self.auth.user_id,
                                         "global": "1",
                                         "page": str(page)},
                                        "getInternationalGames")
            last_page = res["lastPage"]
            page += 1
            for game in res["games"]:
                games.append(game)
        return games

    def request_first_join(self, game_id: int):
        """
        Sends a request to join a game for the first time.

        Args:
            game_id: The ID of the game that the user wishes to join.

        Returns:

        """
        res = self.send_api_request({
            "userID": self.auth.user_id,
            "gameID": game_id,
            "password": ""
        }, "joinGame")
        # TODO Error handling
        return res

    def get_public_ip(self) -> str:
        ip = self.session.get('https://api.ipify.org', proxies=self.proxy).text
        return ip