import logging

from conflict_interface import HubInterface

import creds
from pprint import pprint

from conflict_interface.logger_config import setup_library_logger

if __name__ == "__main__":
    setup_library_logger(logging.DEBUG)
    interface = HubInterface()
    interface.login(creds.username, creds.password)
    game = interface.join_game(9709744)
    city = next(iter(game.get_my_provinces(name="Tangier").values()))
    motorized_infantry_lvl_1 = game.get_unit_types(type_name="Motorized Infantry")
    pprint(motorized_infantry_lvl_1)
    modable_upgrade = city.get_possible_upgrade(id=motorized_infantry_lvl_1.id)
    if city.is_upgrade_buildable(modable_upgrade):
        print(f"Queued to build upgrade of type: .{motorized_infantry_lvl_1.upgrade_name} in Province {city.name}")
        city.build_upgrade(modable_upgrade)
    else:
        print(f"Cannot build upgrade of type {motorized_infantry_lvl_1.upgrade_name} in Province {city.name}")
    game.update()