import logging

from conflict_interface import HubInterface

import creds

from conflict_interface.logger_config import setup_library_logger

if __name__ == "__main__":
    setup_library_logger(logging.DEBUG)
    interface = HubInterface()
    interface.login(creds.username, creds.password)
    game = interface.join_game(9759068)
    city = next(iter(game.get_my_provinces(name="Zaragoza").values()))
    arms_lvl_1 = game.get_upgrade_type_by_name_and_tier('Arms Industry', 1)
    modable_upgrade = city.get_possible_upgrade(id=arms_lvl_1.id)
    if city.is_upgrade_buildable(modable_upgrade):
        print(f"Queued to build upgrade of type: .{arms_lvl_1.upgrade_name} in Province {city.name}")
        city.build_upgrade(modable_upgrade)
    else:
        print(f"Cannot build upgrade of type {arms_lvl_1.upgrade_name} in Province {city.name}")
        print("Canceling construction")
        city.cancel_construction()
        game.update()
        city.cancel_construction()
    game.update()