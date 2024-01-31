from conflict_interface import ConflictInterface
from data_types.relationship import RelationType

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
        print(game.get_relationships(sender_id=9))
        print(time()-t1)
        sleep(3)
