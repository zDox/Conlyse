import json
import logging
from pprint import pprint

from conflict_interface import HubInterface
from conflict_interface.data_types import Point
from conflict_interface.logger_config import setup_library_logger

if __name__ == "__main__":
    setup_library_logger(logging.DEBUG)
    interface = HubInterface()
    with open('../tests/credentials.json') as f:
        creds = json.load(f)

    interface.login(creds["TEST_ACCOUNT_USERNAME"], creds["TEST_ACCOUNT_PASSWORD"])
    print("Starting example")
    game_id = 9758559
    pprint(f"Joining new game:  {game_id}")
    game = interface.join_game(game_id)
    city = game.get_provinces_by_name("Johannesburg")
    army = game.get_army_by_number(14)
    unit_type = game.get_unit_type_by_name_and_tier("Motorized Infantry", 1)

    split_units = [(unit_type.id, 1)]
    target = city.static_data.center_coordinate
    army.split_army(target, split_units)
    game.update()