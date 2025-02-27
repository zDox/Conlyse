import logging

from conflict_interface import HubInterface

import creds
from pprint import pprint

from conflict_interface.logger_config import setup_library_logger

if __name__ == "__main__":
    setup_library_logger(logging.DEBUG)
    interface = HubInterface()
    interface.login(creds.username, creds.password)
    print("Starting example")

    pprint(f"Joining new game:  {9709963}")
    game = interface.join_game(9709963)

    pprint(game.get_upgrade_types(upgrade_identifier="Arms Industry"))