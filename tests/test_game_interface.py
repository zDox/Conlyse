import unittest

from conflict_interface.data_types.newest.version import VERSION
from conflict_interface.interface.hub_interface import HubInterface
from tests.helper_functions import load_credentials, get_test_game_id


class GameInterfaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.username, cls.password, cls.email, cls.proxy_url = load_credentials()
        cls.random_prefix = "test_"

    def setUp(self):
        self.hub_interface = HubInterface(VERSION)
        self.hub_interface.login(self.username, self.password)
        self.game_id = get_test_game_id(self.hub_interface)
        self.game = self.hub_interface.join_game(self.game_id)


