from game_api import GameAPI
from data_types.utils import Position
from data_types.team_profile import TeamProfile
from data_types.player_profile import PlayerProfile
from data_types.province import Province, ProvinceProperty
from data_types.game_info import GameInfo
from data_types.article import Article
from data_types.army import Army
from data_types.commands import Command
from data_types.relationship import RelationType
from data_types.resource_profile import ResourceProfile
from data_types.upgrade import UpgradeType
from data_types.states import States


class GameInterface:
    def __init__(self, game_id: int, game_api: GameAPI):
        self.game_api = game_api
        self.game_id = game_id
        self.player_id = 0
        self.state = None

        self.join_game()

    def join_game(self, guest=False):
        self.game_api.load_game_site()
        self.player_id = self.game_api.request_first_game_activation(guest)

        static_map_data = self.game_api.get_static_map_data()
        self.state = self.game_api.request_login_action()
        self.state.map_state.set_static_map_data(static_map_data)

    def select_country(self, country_id=-1, team_id=-1,
                       random_country_team=False):
        self.player_id = self.game_api.\
                request_selected_country(country_id, team_id,
                                         random_country_team)

        self.game_api.get_static_map_data()
        self.game_api.request_login_action()

    def update(self) -> States:
        new_states = self.game_api.request_game_update()
        print(new_states)
        self.state.update(new_states)
        return self.state

    """
    PlayerState(1)
    """

    def get_player(self, player_id) -> PlayerProfile | None:
        return self.state.player_state.players.get(player_id)

    def list_playable_countries(self) -> dict[int, PlayerProfile]:
        return {player.id: player
                for player in self.state.player_state.players.values()
                if player.available}

    def get_human_players(self) -> dict[int, PlayerProfile]:
        return {player.id: player
                for player in self.state.player_state.players.values()
                if not player.native_computer}

    def get_teams(self) -> dict[int, TeamProfile]:
        return self.state.player_state.teams

    def get_team(self, team_id) -> TeamProfile | None:
        return self.state.player_state.teams.get(team_id)

    """
    NewspaperState(2)
    """

    def get_articles(self, day):
        pass

    def get_current_articles(self) -> dict[int, Article]:
        return self.state.newspaper_state.articles

    """
    MapState(3)
    """

    def get_player_resource_production(self, player_id) -> dict[int, float]:
        pass

    def get_provinces(self) -> dict[int, Province]:
        return self.state.map_state.provinces

    """
    ArmyState(6)
    """

    def get_armies(self) -> dict[int, Army]:
        return self.state.army_state.armies

    def get_my_armies(self) -> dict[int, Army]:
        return {army.id: army
                for army in self.state.army_state.armies.values()
                if army.owner_id == self.player_id}

    def get_army(self, army_id: int) -> Army:
        self.state.army_state.armies.get(army_id)

    def find_path(self, army_id: int, position=Position) -> [Command]:
        # Find Path for a army in the current game to a position
        pass

    def find_path_to_province(self, army_id: int,
                              province_id: int) -> [Command]:
        # Find path for a army in the current game to a province
        pass

    def command_army(army_id: int, command: list[Command]):
        pass
