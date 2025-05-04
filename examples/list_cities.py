import logging


from pprint import pprint


from requests import HTTPError

from conflict_interface.data_types.army_state.unit import Unit
from conflict_interface.interface.hub_interface import HubInterface
from conflict_interface.logger_config import setup_library_logger
from examples.helper_functions import load_credentials


if __name__ == "__main__":
    setup_library_logger(logging.DEBUG)

    interface = HubInterface()
    username, password = "IpXOoCknBFbBKI", "qsubmliInVbgyF"
    interface.login(username, password)

    game = interface.join_game(9832464)
    # Load image from bytes
    print(game.get_my_cities())
