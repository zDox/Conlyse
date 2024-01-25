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
        print(game.state.army_state.armies)
        sleep(5)
