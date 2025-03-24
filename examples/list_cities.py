import logging


from pprint import pprint

from conflict_interface.interface.hub_interface import HubInterface
from conflict_interface.logger_config import setup_library_logger
from examples.helper_functions import load_credentials

if __name__ == "__main__":
    setup_library_logger(logging.DEBUG)

    interface = HubInterface()
    username, password = "QOfUgzqsvWoiMv", "kuHxGrfxPlHbJW"
    interface.login(username, password)

    game = interface.join_game(9874910)
    for army in game.get_armies().values():
        if army.units is None:
            print(army)