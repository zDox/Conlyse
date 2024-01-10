from conflict_interface import ConflictInterface

import creds
from pprint import pprint


if __name__ == "__main__":
    interface = ConflictInterface()
    interface.login(creds.username, creds.password)
    res = interface.get_my_games()
    pprint(res)
    game = interface.join_game(8141919)
    if game.is_country_selection_required():
        game.select_country(3)
