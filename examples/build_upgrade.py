import logging

from conflict_interface.interface.hub_interface import HubInterface
from conflict_interface.logger_config import setup_library_logger
from examples.helper_functions import load_credentials

if __name__ == "__main__":
    setup_library_logger(logging.DEBUG)
    username, password, email, proxy_url = load_credentials()
    interface = HubInterface()
    interface.login(username, password)
    game = interface.join_game(10573372)
    city = next(iter(game.get_my_provinces(name="Bamako").values()))
    arms_lvl_1 = game.get_upgrade_type_by_name_and_tier('Army Base', 1)
    modable_upgrade = city.get_possible_upgrade(id=arms_lvl_1.id)
    if city.is_upgrade_buildable(modable_upgrade):
        print(f"Queued to build upgrade of type: {arms_lvl_1.upgrade_name} in Province {city.name}")
        city.build_upgrade(modable_upgrade)
    else:
        print(f"Cannot build upgrade of type {arms_lvl_1.upgrade_name} in Province {city.name}")
        print("Canceling construction")
        city.cancel_construction()
        game.update()
        city.cancel_construction()
    game.update()