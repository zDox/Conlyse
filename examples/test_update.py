from conflict_interface import HubInterface
from examples.helper_functions import load_credentials

if __name__ == "__main__":
    print("Starting game join example with specific country")
    interface = HubInterface()
    username, password, email, proxy_url = load_credentials()
    interface.login(username, password)
    game_id = list(interface.get_my_games().values())[0].game_id
    game = interface.join_game(game_id)
    print("Country is selected: ", game.is_country_selected())
    print("Selected country:", game.get_player(game.player_id).nation_name)
    game.update()