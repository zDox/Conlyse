import logging
from conflict_interface.data_types import ModableUpgrade
from conflict_interface import HubInterface

import creds
from pprint import pprint

from conflict_interface.logger_config import setup_library_logger

if __name__ == "__main__":
    setup_library_logger(logging.DEBUG)
    interface = HubInterface()
    interface.login(creds.username, creds.password)
    game = interface.join_game(9759068)
    pprint(game.game_state.states.map_state.properties)
    city = next(iter(game.get_my_provinces(name="Madrid").values()))
    pprint(city)
    arms_lvl_1 = game.get_upgrade_type_by_name_and_tier('Arms Industry', 1)
    modable_upgrade = city.get_possible_upgrades(id=arms_lvl_1.id)[0]
    city.build_upgrade(modable_upgrade)
    game.update()