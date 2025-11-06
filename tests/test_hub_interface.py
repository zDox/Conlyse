import unittest

from conflict_interface.interface.hub_interface import HubInterface
from conflict_interface.utils.exceptions import AuthenticationException
from tests.helper_functions import get_new_game_id
from tests.helper_functions import load_credentials

random_prefix = "test_"

class HubInterfaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.username, cls.password, cls.email, cls.proxy_url = load_credentials()

        # Create a shared interface instance and log in once for all non-login tests
        # Reason: Rate limiting of number of logins
        cls.shared_interface = HubInterface()
        cls.shared_interface.login(cls.username, cls.password)

    # Login tests created their own HubInterface in order to properly reset it
    def test_login_success(self):
        interface = HubInterface()
        try:
            interface.login(self.username, self.password)
        except Exception as e:
            self.fail(f"Login raised an exception unexpectedly: {e}")

    def test_login_with_username_failure(self):
        interface = HubInterface()
        with self.assertRaises(AuthenticationException):
            interface.login(random_prefix + self.username, self.password)

    def test_login_with_password_failure(self):
        interface = HubInterface()
        with self.assertRaises(AuthenticationException):
            interface.login(self.username, random_prefix + self.password)

    def test_join_game_failure(self):
        with self.assertRaises(Exception):  # Replace with a specific exception if applicable
            self.shared_interface.join_game(-1)  # Invalid game ID

    def test_get_my_games_success(self):
        try:
            my_games = self.shared_interface.get_my_games()
            self.assertIsNotNone(my_games, "get_my_games returned None unexpectedly.")
        except Exception as e:
            self.fail(f"get_my_games() raised an exception unexpectedly: {e}")

    def test_get_global_games_success(self):
        try:
            global_games = self.shared_interface.get_global_games()
            self.assertIsNotNone(global_games, "get_global_games returned None unexpectedly.")
        except Exception as e:
            self.fail(f"get_global_games() raised an exception unexpectedly: {e}")

    def test_is_in_game_failure(self):
        self.assertFalse(self.shared_interface.is_in_game(-1))

    def test_game_join_as_guest(self):
        try:
            game = self.shared_interface.join_game(get_new_game_id(self.shared_interface), guest=True)
        except Exception as e:
            self.fail(f"join_game() raised an exception unexpectedly: {e}")
        self.assertIsNotNone(game)
"""
    def test_game_join_with_proxy(self):
        proxy = {
            "http": self.proxy_url,
            "https": self.proxy_url,
        }
        proxy_interface = HubInterface()
        ip_without_proxy = proxy_interface.get_public_ip()
        proxy_interface.set_proxy(proxy)
        ip_with_proxy = proxy_interface.get_public_ip()
        self.assertNotEqual(ip_without_proxy, ip_with_proxy)
        proxy_interface.login(self.username, self.password)
        try:
            game = proxy_interface.join_game(get_new_game_id(proxy_interface), guest=True)
        except Exception as e:
            self.fail(f"join_game() raised an exception unexpectedly: {e}")
        self.assertIsNotNone(game)
"""