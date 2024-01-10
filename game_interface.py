from game_api import GameAPI


class GameInterface:
    def __init__(self, game_id: int, game_api: GameAPI):
        self.game_api = game_api
        self.game_id = game_id
        self.join_game()

    def join_game(self):
        self.game_api.load_game_site()
        self.game_api.get_static_map_data()
        print(self.game_api.activate_game())
        self.game_api.make_game_login_action()
