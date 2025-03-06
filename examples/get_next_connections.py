import json
import logging
from pprint import pprint

from conflict_interface import HubInterface
from conflict_interface.logger_config import setup_library_logger

if __name__ == "__main__":
    setup_library_logger(logging.DEBUG)
    interface = HubInterface()
    with open('../tests/credentials.json') as f:
        creds = json.load(f)


    interface.login(creds["TEST_ACCOUNT_USERNAME"], creds["TEST_ACCOUNT_PASSWORD"])
    print("Starting example")
    game_id = 9709744
    pprint(f"Joining new game:  {game_id}")
    game = interface.join_game(game_id)

    a = list(game.get_my_armies().values())[0].get_next_connections()
    print(a)