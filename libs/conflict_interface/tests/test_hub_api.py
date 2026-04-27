import unittest

from conflict_interface.api.hub_api import HubApi
from conflict_interface.utils.exceptions import AuthenticationException
from helper_functions import load_credentials


class HubApiTests(unittest.TestCase):
    """
    Unit tests for the HubApi class, which provides methods for interacting with the hub API.
    """

    RANDOM_PREFIX = "test_"

    @classmethod
    def setUpClass(cls):
        """
        Class-level setup method to load shared credentials for all tests.
        """
        cls.username, cls.password, cls.email, cls.proxy_url = load_credentials()

    def setUp(self):
        """
        Instance-level setup method to initialize a new HubApi instance for each test.
        """
        self.hub_api = HubApi()

    def _generate_random_username(self):
        """
        Helper method to generate a random username by appending a prefix to the loaded username.
        """
        return self.RANDOM_PREFIX + self.username

    def _generate_random_email(self):
        """
        Helper method to generate a random email by appending a prefix to the loaded email.
        """
        return self.RANDOM_PREFIX + self.email

    def _login_and_check(self, username, password):
        """
        Helper method to log in and assert that the login was successful.
        """
        self.assertTrue(self.hub_api.login(username, password))

    def test_check_login(self):
        """
        Test that the `check_login` method returns True for valid credentials.
        """
        self.assertTrue(self.hub_api.check_login(self.username, self.password))

    def test_check_login_with_invalid_password(self):
        """
        Test that the `check_login` method returns False for an invalid password.
        """
        self.assertFalse(self.hub_api.check_login(self.username, self.RANDOM_PREFIX + self.password))

    def test_check_login_with_invalid_username(self):
        """
        Test that the `check_login` method returns False for an invalid username.
        """
        self.assertFalse(self.hub_api.check_login(self._generate_random_username(), self.password))

    def test_check_username_availability(self):
        """
        Test that the `check_username_available` method correctly identifies available and unavailable usernames.
        """
        self.assertTrue(self.hub_api.check_username_available(self._generate_random_username()))
        self.assertFalse(self.hub_api.check_username_available(self.username))

    def test_check_email_availability(self):
        """
        Test that the `check_email_available` method correctly identifies available and unavailable emails.
        """
        self.assertTrue(self.hub_api.check_email_available(self._generate_random_email()))
        self.assertFalse(self.hub_api.check_email_available(self.email))

    def test_load_main_page(self):
        """
        Test that the `load_main_page` method returns the correct action URL and expected form data keys.
        """
        action, data = self.hub_api.load_main_page()
        self.assertTrue(action.startswith("index.php") and action.endswith("source=browser-desktop"))
        expected_keys = ["sg[reg][username]", "sg[reg][email]", "sg[reg][password]",
                         "sg[reg][action]", "sg_cs", "sg_cst", "sg_csh"]
        self.assertCountEqual(expected_keys, data.keys())

    def test_login(self):
        """
        Test that the `login` method successfully logs in with valid credentials.
        """
        self._login_and_check(self.username, self.password)

    def test_login_with_invalid_password(self):
        """
        Test that the `login` method returns False for an invalid password.
        """
        self.assertFalse(self.hub_api.login(self.username, self.RANDOM_PREFIX + self.password))

    def test_logout(self):
        """
        Test that the `logout` method clears authentication and allows re-login.
        """
        self._login_and_check(self.username, self.password)
        self.hub_api.logout()
        self.assertIsNone(self.hub_api.auth)
        self._login_and_check(self.username, self.password)

    def test_my_games(self):
        """
        Test that the `get_my_games` method returns a list of games for an authenticated user.
        """
        self._login_and_check(self.username, self.password)
        games = self.hub_api.get_my_games()
        self.assertIsInstance(games, list)
        self.assertGreaterEqual(len(games), 0)

    def test_my_games_unauthenticated(self):
        """
        Test that the `get_my_games` method raises an AuthenticationException for unauthenticated users.
        """
        with self.assertRaises(AuthenticationException):
            self.hub_api.get_my_games()

    def test_global_games(self):
        """
        Test that the `get_global_games` method returns a list of games for an authenticated user.
        """
        self._login_and_check(self.username, self.password)
        games = self.hub_api.get_global_games()
        self.assertIsInstance(games, list)
        self.assertGreaterEqual(len(games), 0)

    def test_global_games_unauthenticated(self):
        """
        Test that the `get_global_games` method raises an AuthenticationException for unauthenticated users.
        """
        with self.assertRaises(AuthenticationException):
            self.hub_api.get_global_games()