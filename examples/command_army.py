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
    city = game.get_provinces_by_name("Maun")
    infantry = game.get_army_by_number(8)
    target = city.static_data.center_coordinate
    infantry.set_waypoint(target)
    game.update()