import logging


from pprint import pprint

from conflict_interface.hub_interface import HubInterface
from conflict_interface.logger_config import setup_library_logger
from examples.helper_functions import load_credentials

if __name__ == "__main__":
    setup_library_logger(logging.DEBUG)

    interface = HubInterface()
    username, password, email, proxy_url = load_credentials()
    interface.login(username, password)

    game = interface.join_game(9758559)

    pprint(game.get_my_cities())