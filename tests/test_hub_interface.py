import os
import unittest

from conflict_interface.hub_interface import HubInterface
from conflict_interface.utils.exceptions import AuthenticationException
from tests.load_credentials import load_credentials


random_prefix = "test_"

class HubInterfaceTests(unittest.TestCase):
    def setUpClass(cls):
        cls.username, cls.password, cls.email = load_credentials()

    def setUp(self):
        self.interface = HubInterface()

    def test_login_success(self):
        try:
            self.interface.login(self.username, self.password)
        except Exception as e:
            self.fail(f"Login raised an exception unexpectedly: {e}")
    
    
    def test_login_with_username_failure(self):
        with self.assertRaises(AuthenticationException):
            self.interface.login(random_prefix+self.username, self.password)
            
    def test_login_with_password_failure(self):
        with self.assertRaises(AuthenticationException):
            self.interface.login(self.username, random_prefix+self.password)

    def test_join_game_failure(self):
        self.interface.login(self.username, self.password)
        with self.assertRaises(Exception):  # Replace with a specific exception if applicable
            self.interface.join_game(-1)  # Invalid game ID

    def test_get_my_games_success(self):
        self.interface.login(self.username, self.password)
        try:
            my_games = self.interface.get_my_games()
            self.assertIsNotNone(my_games, "get_my_games returned None unexpectedly.")
        except Exception as e:
            self.fail(f"get_my_games() raised an exception unexpectedly: {e}")

    def test_get_global_games_success(self):
        self.interface.login(self.username, self.password)
        try:
            global_games = self.interface.get_global_games()
            self.assertIsNotNone(global_games, "get_global_games returned None unexpectedly.")
        except Exception as e:
            self.fail(f"get_global_games() raised an exception unexpectedly: {e}")

    def test_is_in_game_failure(self):
        self.interface.login(self.username, self.self.password)
        self.assertFalse(self.interface.is_in_game(-1))