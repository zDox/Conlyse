from conflict_interface import HubInterface

import creds
from pprint import pprint

if __name__ == "__main__":
    interface = HubInterface()
    interface.login(creds.username, creds.password)
    print("Starting example")

    pprint(f"Joining new game:  {9709963}")
    game = interface.join_game(9709963)

    pprint(game.get_upgrade_types(upgrade_identifier="Arms Industry"))