import logging

import creds
from pprint import pprint

from conflict_interface.hub_interface import HubInterface
from conflict_interface.logger_config import setup_library_logger


if __name__ == "__main__":
    setup_library_logger(logging.DEBUG)

    interface = HubInterface()
    interface.login(creds.username, creds.password)

    game = interface.join_game(9748894)

    pprint(game.get_my_cities())