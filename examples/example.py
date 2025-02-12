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
    game = interface.join_game(9703362)

    game.update()
    t1 = time()
    pprint(game.get_current_articles())
    pprint(game.relative_time_since_start(game.get_last_uptime()))
    pprint(game.state.game_info_state.game_info)
    pprint(game.game_api.time_stamps)
    pprint(game.get_last_uptime())
    pprint(game.get_articles(game.state.game_info_state.game_info.day_of_game))
    sleep(3)
