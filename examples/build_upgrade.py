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
    pprint(game.get_my_provinces())
    city = next(iter(game.get_my_provinces(name="Madrid").values()))
    pprint(city)
    arms_lvl_1 = game.get_upgrade_type_by_name_and_tier('Arms Industry', 1)
    city.build_upgrade(ModableUpgrade(
        id=arms_lvl_1.id,
        condition=0,
        constructing=False,
        enabled=False,
        relative_position=None,
        premium_level=0,
    ))
    game.update()