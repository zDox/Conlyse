import logging


from pprint import pprint

from conflict_interface.data_types.hub_types.hub_game_state_enum import HubGameState
from conflict_interface.data_types.map_state.map_state_enums import ProvinceStateID
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
    city = next(iter(game.get_my_cities().values()))
    arms_lvl_1 = game.get_upgrade_type_by_name_and_tier('Army Base', 1)
    modable_upgrade = city.get_possible_upgrade(id=arms_lvl_1.id)
    if city.is_upgrade_buildable(modable_upgrade):
        print(f"Queued to build upgrade of type: {arms_lvl_1.upgrade_name} in Province {city.name}")
        city.build_upgrade(modable_upgrade)
        game.update()
    else:
        print(f"Cannot build upgrade of type {arms_lvl_1.upgrade_name} in Province {city.name}")
        print("Canceling construction")
        city.cancel_construction()
        game.update()
        city.cancel_construction()