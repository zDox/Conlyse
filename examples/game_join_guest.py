from conflict_interface.utils.exceptions import CountryUnselectedException

from conflict_interface import HubInterface
from conflict_interface.data_types.hub_game_info import HubGameState


import creds
from pprint import pprint

if __name__ == "__main__":
    print("Starting game join example as guest")
    interface = HubInterface()
    interface.login(creds.username, creds.password)
    games = interface.get_global_games(scenario_id=5975, # World war 3 1x speed
                                       state=HubGameState.READY_TO_JOIN)
    selected_game = next(iter(games.values()))
    pprint(f"Joining new game:  {selected_game.game_id}")
    game = interface.join_game(selected_game.game_id, guest=True)
    print("Country is selected: ", game.is_country_selected())

    print("Selected country:", game.get_player(game.player_id).nation_name)
    game.update()