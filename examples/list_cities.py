

import creds
from pprint import pprint

from conflict_interface.hub_interface import HubInterface

if __name__ == "__main__":
    interface = HubInterface()
    interface.login(creds.username, creds.password)
    print("Starting example")

    pprint(f"Joining new game:  {9748894}")
    game = interface.join_game(9748894)
    print("Loaded Game")

    pprint(game.get_my_cities())