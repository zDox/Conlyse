import logging
from pprint import pprint

from conflict_interface.interface.hub_interface import HubInterface
from conflict_interface.logger_config import setup_library_logger
from examples.helper_functions import load_credentials

if __name__ == "__main__":
    setup_library_logger(logging.DEBUG)
    interface = HubInterface()
    username, password, email, proxy_url = load_credentials()


    interface.login(username, password)
    print("Starting example")
    game_id = 9709744
    pprint(f"Joining new game:  {game_id}")
    game = interface.join_game(game_id)

    print(list(game.get_my_provinces().values())[0].static_data.borders)
    print(game.game_state.states.map_state.map.get_connections()[0: 100])