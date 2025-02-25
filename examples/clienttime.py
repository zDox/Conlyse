from conflict_interface import ConflictInterface
from examples import creds

if __name__ == "__main__":
    print("Starting game join example with specific country")
    interface = ConflictInterface()
    interface.login(creds.username, creds.password)
    game_id = list(interface.get_my_games().values())[0].game_id
    game = interface.join_game(game_id)
    print("Country is selected: ", game.is_country_selected())
    print("Selected country:", game.get_player(game.player_id).nation_name)
