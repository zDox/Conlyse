import json
import logging
from pprint import pprint

from conflict_interface.data_types.game_object import dump_dataclass
from conflict_interface.interface.hub_interface import HubInterface
from conflict_interface.logger_config import setup_library_logger
from examples.helper_functions import load_credentials

if __name__ == "__main__":
    setup_library_logger(logging.DEBUG)
    interface = HubInterface()
    username, password, email, proxy_url = load_credentials()
    interface.login(username, password)
    print("Starting example")

    pprint(f"Joining new game:  {9709744}")
    game = interface.join_game(9709744)
    print("Loaded Game")

    res = dump_dataclass(game.get_players()[1])

    out = json.dumps(res)

    print(out)