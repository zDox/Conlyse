from game_api import GameAPI
from data_types.game_activation_result import GameActivationResult, \
        GameActivationResult_to_exception
from pprint import pprint


class GameInterface:
    def __init__(self, game_id: int, game_api: GameAPI):
        self.game_api = game_api
        self.game_id = game_id
        self.state = None

        self.join_game()

    def join_game(self):
        self.game_api.load_game_site()
        activation_result = self.game_api.request_first_game_activation()
        if activation_result != GameActivationResult.SUCCESS:
            pass
            # raise GameActivationResult_to_exception(activation_result)

        static_map_data = self.game_api.get_static_map_data()
        self.state = self.game_api.request_login_action()
        self.state.map_state.set_static_map_data(static_map_data)

    def select_country(self, country_id=-1, team_id=-1,
                       random_country_team=False):
        res = self.game_api.request_selected_country(country_id, team_id,
                                                     random_country_team)

        if res != GameActivationResult.SUCCESS:
            pass
            # raise GameActivationResult_to_exception(res)

        self.game_api.get_static_map_data()
        self.game_api.request_login_action()

    def list_playable_countries(self):
        return [player for player
                in self.state.player_state.players.values()
                if player.available]

    def update(self):
        new_states = self.game_api.request_game_update()
        self.state.update(new_states)
        return self.state
