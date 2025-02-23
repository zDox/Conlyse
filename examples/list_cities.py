import os
import sys
import inspect

currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)

from conflict_interface import ConflictInterface

import creds
from pprint import pprint

if __name__ == "__main__":
    interface = ConflictInterface()
    interface.login(creds.username, creds.password)
    print("Starting example")

    pprint(f"Joining new game:  {9748894}")
    game = interface.join_game(9748894)
    print("Loaded Game")

    pprint(game.get_my_cities())