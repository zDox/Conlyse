import logging
from time import sleep


from conflict_interface.interface.hub_interface import HubInterface
from conflict_interface.logger_config import setup_library_logger
from examples.helper_functions import load_credentials

if __name__ == "__main__":
    setup_library_logger(logging.DEBUG)
    username, password, email, proxy_url = load_credentials()
    itf = HubInterface()
    itf.login(username, password)
    game = itf.join_game(9812061, replay_filename="replay.db")
    while True:
        game.update()
        sleep(10)