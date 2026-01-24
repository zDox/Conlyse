import logging
from time import sleep

from conflict_interface.logger_config import setup_library_logger

from conflict_interface.interface.hub_interface import HubInterface
from conflict_interface.data_types.hub_types.hub_game_state_enum import HubGameState

from pprint import pprint

from examples.helper_functions import load_credentials


if __name__ == "__main__":
    print("Starting game join example as guest")
    setup_library_logger(logging.DEBUG)
    username, password, email, proxy_url = load_credentials()
    interface = HubInterface()
    interface.login(username, password)
    games = interface.get_global_games(scenario_id=5975, # World war 3 1x speed
                                       state=HubGameState.READY_TO_JOIN)
    selected_game = next(iter(games))
    pprint(f"Joining new game:  {selected_game.game_id}")
    game = interface.join_game(selected_game.game_id, guest=True, replay_filename="replay.db")
    print("Country is selected: ", game.is_country_selected())

    print("Selected country:", game.get_player(game.player_id).nation_name)
    print(game.get_player(-1))
    game.update()
    sleep(10)
    game.update()

