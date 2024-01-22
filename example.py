from conflict_interface import ConflictInterface

import creds
from pprint import pprint
from time import sleep, time


if __name__ == "__main__":
    interface = ConflictInterface()
    interface.login(creds.username, creds.password)
    print(interface.get_my_games())
    game = interface.join_game(8141618)

    while True:
        pprint("Updating Game State")
        time1 = time()
        game.update()
        total = time() - time1
        pprint(game.state.game_info_state.game_info)
        print(f"Updating took {total}s")
        sleep(5)
