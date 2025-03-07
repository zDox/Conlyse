import logging

from conflict_interface import HubInterface
from conflict_interface.logger_config import setup_library_logger
from examples.helper_functions import load_credentials

if __name__ == "__main__":
    print("Starting game join example with specific country")
    setup_library_logger(logging.DEBUG)
    username, password, email, proxy_url = load_credentials()
    interface = HubInterface()
    interface.login(username, password)

    game_id = list(interface.get_my_games().values())[1].game_id
    game = interface.join_game(game_id)
    print("Country is selected: ", game.is_country_selected())
    print("Selected country:", game.get_player(game.player_id).nation_name)

    print(game.game_api.client_time(1)-game.game_state.states.game_info_state.start_of_game)
    print(game.game_api.client_time(4))