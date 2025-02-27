import logging

from conflict_interface import HubInterface

import creds
from pprint import pprint

from conflict_interface.logger_config import setup_library_logger

if __name__ == "__main__":
    setup_library_logger(logging.DEBUG)
    interface = HubInterface()
    interface.login(creds.username, creds.password)
    city_name = "Hargeisa"
    game_id = 9709963
    print(f"Starting Mobilization example on {city_name} in game {game_id} with infantry")

    pprint(f"Joining new game:  {game_id}")
    game = interface.join_game(game_id)
    pprint(f"Loaded game:  {game_id}")

    city = next(iter(game.get_my_provinces(name=city_name).values()))
    pprint(city)
    unit_type = next(iter(game.get_unit_types(type_name="Motorized Infantry")))
    game.update()