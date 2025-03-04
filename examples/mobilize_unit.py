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
    city = next(iter(game.get_my_provinces(name="Rabat").values()))
    print(city.production)
    print(city.productions)
    motorized_infantry_lvl_1 = game.get_unit_type_by_name_and_tier("Motorized Infantry", 4)
    target = None
    for production in city.get_possible_productions():
        if production.unit.unit_type_id == motorized_infantry_lvl_1.id:
            target = production
    print(target)
    city.mobilize_unit(target)
    game.update()