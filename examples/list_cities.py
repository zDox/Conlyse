import logging


from pprint import pprint

from conflict_interface.data_types.player_state.faction import Faction
from conflict_interface.interface.hub_interface import HubInterface
from conflict_interface.logger_config import setup_library_logger
from examples.helper_functions import load_credentials

if __name__ == "__main__":
    setup_library_logger(logging.DEBUG)

    interface = HubInterface()
    username, password = "QOfUgzqsvWoiMv", "kuHxGrfxPlHbJW"
    interface.login(username, password)

    game = interface.join_game(9874910)
    for country in game.get_players().values():
        pprint(country)

    liste = []

    test = Faction.WESTERN
    print(test.code)
    test = Faction.EASTERN
    print(test.code)
    test = Faction.EUROPEAN
    print(test.code)