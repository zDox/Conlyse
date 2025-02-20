import os
import sys
import inspect

from conflict_interface.data_types.upgrades.upgrade import ModableUpgrade

currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)

from conflict_interface import ConflictInterface

import creds
from pprint import pprint
from time import sleep, time


if __name__ == "__main__":
    interface = ConflictInterface()
    interface.login(creds.username, creds.password)
    print("Starting example")

    pprint(f"Joining new game:  {9709963}")
    game = interface.join_game(9709963)

    pprint(game.get_upgrade_types(upgrade_identifier="Arms Industry"))