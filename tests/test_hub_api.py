import unittest

from conflict_interface.hub_api import HubApi
from conflict_interface.utils.exceptions import AuthenticationException
from tests.helper_functions import load_credentials


class HubApiTests(unittest.TestCase):
    RANDOM_PREFIX = "test_"

    @classmethod
    def setUpClass(cls):
        # Load shared credentials once for the class
        cls.username, cls.password, cls.email, cls.proxy_url = load_credentials()

    def setUp(self):
        self.hub_api = HubApi()

    def _generate_random_username(self):
        return self.RANDOM_PREFIX + self.username

    def _generate_random_email(self):
        return self.RANDOM_PREFIX + self.email

    def _login_and_check(self, username, password):
        # Reusable login assertion
        self.assertTrue(self.hub_api.login(username, password))

    def test_check_login(self):
        self.assertTrue(self.hub_api.check_login(self.username, self.password))

    def test_check_login_with_invalid_password(self):
        self.assertFalse(self.hub_api.check_login(self.username, self.RANDOM_PREFIX + self.password))

    def test_check_login_with_invalid_username(self):
        self.assertFalse(self.hub_api.check_login(self._generate_random_username(), self.password))

    def test_check_username_availability(self):
        self.assertTrue(self.hub_api.check_username_available(self._generate_random_username()))
        self.assertFalse(self.hub_api.check_username_available(self.username))

    def test_check_email_availability(self):
        self.assertTrue(self.hub_api.check_email_available(self._generate_random_email()))
        self.assertFalse(self.hub_api.check_email_available(self.email))

    def test_load_main_page(self):
        action, data = self.hub_api.load_main_page()
        self.assertTrue(action.startswith("index.php") and action.endswith("source=browser-desktop"))
        expected_keys = ["sg[reg][username]", "sg[reg][email]", "sg[reg][password]",
                         "sg[reg][action]", "sg_cs", "sg_cst", "sg_csh"]
        self.assertCountEqual(expected_keys, data.keys())

    def test_login(self):
        self._login_and_check(self.username, self.password)

    def test_login_with_invalid_password(self):
        self.assertFalse(self.hub_api.login(self.username, self.RANDOM_PREFIX + self.password))

    def test_logout(self):
        self._login_and_check(self.username, self.password)
        self.hub_api.logout()
        self.assertIsNone(self.hub_api.auth)
        self._login_and_check(self.username, self.password)

    def test_my_games(self):
        self._login_and_check(self.username, self.password)
        games = self.hub_api.get_my_games()
        self.assertIsInstance(games, list)
        self.assertGreaterEqual(len(games), 0)

    def test_my_games_unauthenticated(self):
        with self.assertRaises(AuthenticationException):
            self.hub_api.get_my_games()

    def test_global_games(self):
        self._login_and_check(self.username, self.password)
        games = self.hub_api.get_global_games()
        self.assertIsInstance(games, list)
        self.assertGreaterEqual(len(games), 0)

    def test_global_games_unauthenticated(self):
        with self.assertRaises(AuthenticationException):
            self.hub_api.get_global_games()
