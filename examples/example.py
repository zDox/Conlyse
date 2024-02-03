import os
import sys
import inspect

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
    print(interface.get_my_games())
    game = interface.join_game(8141617)

    while True:
        game.update()
        t1 = time()
        print(type(list(game.get_teams().values())[0]))
        sleep(3)
