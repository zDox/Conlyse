from conflict_interface import ConflictInterface

import creds
from pprint import pprint


if __name__ == "__main__":
    interface = ConflictInterface()
    interface.login(creds.username, creds.password)
    game = interface.join_game(8141919)
    print(game.list_playable_countries())
