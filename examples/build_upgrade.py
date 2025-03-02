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
    game = interface.join_game(9709744)
    city = next(iter(game.get_my_provinces(name="Rabat").values()))
    pprint(city)
    pprint(city.get_possible_upgrades())
    arms_lvl_1 = game.get_upgrade_type_by_name_and_tier('Arms Industry', 2)
    pprint(arms_lvl_1)
    modable_upgrade = city.get_possible_upgrade(id=arms_lvl_1.id)
    pprint(modable_upgrade)
    city.build_upgrade(modable_upgrade)
    game.update()