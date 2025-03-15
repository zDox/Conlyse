import logging


from pprint import pprint
from time import sleep

from conflict_interface.interface.hub_interface import HubInterface
from conflict_interface.logger_config import setup_library_logger
from examples.helper_functions import load_credentials

if __name__ == "__main__":
    setup_library_logger(logging.DEBUG)

    interface = HubInterface()
    username, password, email, proxy_url = load_credentials()
    interface.login("user9913153", "c7z#76XJ8$$!5Zdf")




    game = interface.join_game(9812061)
    game.record_replay("test.zip")

    while True:
        game.update()
        sleep(5)
