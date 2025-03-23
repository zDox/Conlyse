import logging


from pprint import pprint

from conflict_interface.data_types.hub_types.hub_game_state_enum import HubGameState
from conflict_interface.interface.hub_interface import HubInterface
from conflict_interface.logger_config import setup_library_logger
from examples.helper_functions import load_credentials

if __name__ == "__main__":
    print("Starting game join example with specific country")
    setup_library_logger(logging.DEBUG)
    interface = HubInterface()
    username, password, email, proxy_url = load_credentials()
    interface.login(username, password)
    games = interface.get_global_games(scenario_id=5975, # World war 3 1x speed
                                       state=HubGameState.READY_TO_JOIN)
    my_games = interface.get_my_games()
    selected_game = None
    for game in games:
        if not game.game_id in my_games:
            selected_game = game
            break
    if selected_game is None:
        exit()

    pprint(f"Joining new game:  {selected_game.game_id}")
    game = interface.join_game(selected_game.game_id)
    print(game.player_id)
    print("Country is selected: ", game.is_country_selected())
    selected_country = next(iter(list(game.get_playable_countries().values())))
    print(selected_country)
    game.select_country(country_id=selected_country.player_id)
    print("Country is selected: ", game.is_country_selected())
    print(f"Selected country: {game.get_my_player()}")
    game.update()