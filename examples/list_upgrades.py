import logging

from conflict_interface import HubInterface

from pprint import pprint

from conflict_interface.logger_config import setup_library_logger
from examples.helper_functions import load_credentials

if __name__ == "__main__":
    setup_library_logger(logging.DEBUG)
    interface = HubInterface()
    username, password, email, proxy_url = load_credentials()
    interface.login(username, password)
    print("Starting example")

    pprint(f"Joining new game:  {9709963}")
    game = interface.join_game(9709963)

    pprint(game.get_upgrade_types(upgrade_identifier="Arms Industry"))