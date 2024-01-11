from game_api import GameAPI
from data_types.game_activation_result import GameActivationResult, \
        GameActivationResult_to_exception


class GameInterface:
    def __init__(self, game_id: int, game_api: GameAPI):
        self.game_api = game_api
        self.game_id = game_id
        self.join_game()

    def join_game(self):
        self.game_api.load_game_site()
        self.game_api.get_static_map_data()
        activation_result = self.game_api.request_first_game_activation()
        if activation_result != GameActivationResult.SUCCESS:
            raise GameActivationResult_to_exception(activation_result)

        self.game_api.request_login_action()

    def select_country(self, country_id=-1, team_id=-1,
                       random_country_team=False):
        res = self.game_api.request_selected_country(country_id, team_id,
                                                     random_country_team)

        if res != GameActivationResult.SUCCESS:
            raise GameActivationResult_to_exception(res)

        self.game_api.request_login_action()

    def list_playable_countries(self):
        return self.game_api.request_game_update(with_states=False)
