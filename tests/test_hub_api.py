import os
import unittest

from conflict_interface.hub_api import HubApi
from conflict_interface.utils.exceptions import AuthenticationException
from tests.load_credentials import load_credentials

username, password, email = load_credentials()
random_prefix = "test_"

class HubApiTests(unittest.TestCase):
    def test_check_login(self):
        hub_api = HubApi()
        self.assertTrue(hub_api.check_login(username, password))

    def test_check_login_invalid_password(self):
        hub_api = HubApi()
        self.assertFalse(hub_api.check_login(username, random_prefix+password))

    def test_check_login_invalid_username(self):
        hub_api = HubApi()
        self.assertFalse(hub_api.check_login(random_prefix+username, password))

    def test_check_username_available(self):
        hub_api = HubApi()
        self.assertTrue(hub_api.check_username_available(random_prefix+username))

    def test_check_username_unavailable(self):
        hub_api = HubApi()
        self.assertFalse(hub_api.check_username_available(username))

    def test_check_email_available(self):
        hub_api = HubApi()
        self.assertTrue(hub_api.check_email_available(random_prefix+email))

    def test_check_email_unavailable(self):
        hub_api = HubApi()
        self.assertFalse(hub_api.check_email_available(email))

    def test_load_main_page(self):
        hub_api = HubApi()
        action, data = hub_api.load_main_page()
        self.assertTrue(action.startswith("index.php"))
        self.assertTrue(action.endswith("source=browser-desktop"))
        contained_keys = ["sg[reg][username]", "sg[reg][email]", "sg[reg][password]", "sg[reg][action]", "sg_cs", "sg_cst",
                          "sg_csh"]
        self.assertCountEqual(contained_keys, list(data.keys()))
        
    def test_login(self):
        hub_api = HubApi()
        self.assertTrue(hub_api.login(username, password))
    
    def test_login_invalid_password(self):
        hub_api = HubApi()
        self.assertFalse(hub_api.login(username, random_prefix+password))
        
    def test_logout(self):
        hub_api = HubApi()
        self.assertTrue(hub_api.login(username, password))
        hub_api.logout()
        self.assertTrue(hub_api.auth is None)
        self.assertTrue(hub_api.login(username, password))

    def test_my_games(self):
        hub_api = HubApi()
        self.assertTrue(hub_api.login(username, password))
        games = hub_api.get_my_games()
        self.assertIsInstance(games, list)
        self.assertTrue(len(games) >= 0)

    def test_my_games_unauthenticated(self):
        hub_api = HubApi()
        self.assertRaises(AuthenticationException, hub_api.get_my_games)

    def test_global_games(self):
        hub_api = HubApi()
        self.assertTrue(hub_api.login(username, password))
        games = hub_api.get_global_games()
        self.assertIsInstance(games, list)
        self.assertTrue(len(games) >= 0)

    def test_global_games_unauthenticated(self):
        hub_api = HubApi()
        self.assertRaises(AuthenticationException, hub_api.get_global_games)
