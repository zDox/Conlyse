from conflict_interface import ConflictInterface

import creds
from pprint import pprint

if __name__ == "__main__":
    interface = ConflictInterface()
    interface.login(creds.username, creds.password)
    print("Starting example")

    pprint(f"Joining new game:  {9709963}")
    game = interface.join_game(9709963)

    pprint(game.get_upgrade_types(upgrade_identifier="Arms Industry"))