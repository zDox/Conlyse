import logging
from pprint import pprint

from conflict_interface.interface.hub_interface import HubInterface
from conflict_interface.logger_config import setup_library_logger
from examples.helper_functions import load_credentials

if __name__ == "__main__":
    setup_library_logger(logging.DEBUG)
    username, password, email, proxy_url = load_credentials()

    interface = HubInterface()
    interface.login(username, password)
    city_name = "Hargeisa"
    game_id = 9709963
    print(f"Starting Cancel construction example on {city_name} in game {game_id}")

    pprint(f"Joining new game:  {game_id}")
    game = interface.join_game(game_id)
    pprint(f"Loaded game:  {game_id}")

    city = next(iter(game.get_my_provinces(name=city_name).values()))
    pprint(city)
    city.cancel_construction()
    game.update()