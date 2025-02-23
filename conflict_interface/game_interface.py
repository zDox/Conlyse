from __future__ import annotations

from typing import TYPE_CHECKING

from datetime import datetime, timedelta
from functools import wraps
from typing import Any

from conflict_interface.data_types.map_state.province import UpdateProvinceAction, ProvinceUpdateActionModes, ProvinceStateID
from .game_api import GameAPI
from .utils import Point
from .data_types.states import States
from .data_types.static_map_data import  StaticMapData

if TYPE_CHECKING:
    from .data_types import TeamProfile, PlayerProfile, Province, \
        GameInfo, Article
    from .data_types.resources import ResourceProfile, ResourceEntry
    from .data_types.warfare import Army, Command, UnitType
    from .data_types.upgrades import UpgradeType
from .utils.exceptions import CountryUnselectedException, GameActivationException, GameActivationErrorCodes


class GameInterface:
    def __init__(self, game_id: int, game_api: GameAPI):
        self.game_api = game_api
        self.game_id = game_id
        self.player_id = 0
        self.state: States | None = None

    @staticmethod
    def country_selected(func):
        """Decorator that checks if a country is selected. If not, raises CountryUnselectedError."""

        @wraps(func)
        def wrap(self, *args, **kwargs):
            if self.is_country_selected():
                return func(self, *args, **kwargs)
            else:
                raise CountryUnselectedException("Country not selected.")

        return wrap

    def join_game(self, guest=False):
        self.game_api.load_game_site()
        if not guest:
            try:
                self.player_id = self.game_api.request_game_activation(
                    selected_player_id=-1,
                    selected_team_id=-1,
                    random_team_country_selection=False,
                )
                self.state = States.from_dict(self.game_api.request_login_action(), self)
            except GameActivationException as e:
                if e.error_code != GameActivationErrorCodes.COUNTRY_SELECTION_REQUESTED:
                    raise e
                self.state = States.from_dict(self.game_api.request_game_update(), self)
        else:
            self.state = States.from_dict(self.game_api.request_game_update(), self)
        static_map_data = StaticMapData.from_dict(self.game_api.get_static_map_data(), self)

        self.state.map_state.map.set_static_map_data(static_map_data)

    def select_country(self, country_id=-1, team_id=-1,
                       random_country_team=False):
        self.player_id = self.game_api.request_game_activation(country_id, team_id,
                                              random_country_team)

        self.state = States.from_dict(self.game_api.request_login_action(), self)

    def update(self) -> States:
        new_states = self.game_api.request_game_update()
        self.state.update(new_states)
        return self.state

    """
    Utility functions
    """

    def relative_time_since_start(self, date) -> timedelta:
        return date - self.state.game_info_state.game_info.start_of_game

    def get_last_uptime(self) -> datetime:
        update_times = [datetime.fromtimestamp(int(time_stamp_str) / 1000)
                        for time_stamp_str in self.game_api.time_stamps.values()
                        if time_stamp_str != "java.util.HashMap"]
        return max(update_times)

    def client_time(self):
        datetime.now()

    """
    PlayerState(1)
    """

    def is_country_selected(self) -> bool:
        return self.player_id != 0

    def get_player(self, player_id) -> PlayerProfile | None:
        return self.state.player_state.players.get(player_id)

    def get_my_player(self):
        return self.get_player(self.player_id)

    def get_players(self, **filters) -> dict[int, PlayerProfile]:
        return {player.player_id: player
                for player in self.state.player_state.players.values()
                if all([getattr(player, key) == val
                        for key, val in filters.items()])}

    def get_playable_countries(self) -> dict[int, PlayerProfile]:
        return self.get_players(available=True)

    def get_human_players(self) -> dict[int, PlayerProfile]:
        return self.get_players(computer_player=False)

    def get_teams(self, **filters) -> dict[int, TeamProfile]:
        return {team.team_id: team
                for team in self.state.player_state.teams.values()
                if all(getattr(team, key) == val for key, val in filters.items())}

    def get_team(self, team_id) -> TeamProfile | None:
        return self.state.player_state.teams.get(team_id)

    """
    NewspaperState(2)
    """

    def get_articles(self, day):
        return {article_id: article
                for article_id, article in self.state.newspaper_state.articles.items()
                if self.relative_time_since_start(article.time_stamp).days + 1 == day}

    def get_current_articles(self) -> dict[int, Article]:
        return self.state.newspaper_state.articles

    """
    MapState(3)
    """

    def get_provinces(self, **filters) -> dict[int, Province]:
        res = {}
        for province in self.state.map_state.map.locations:
            if all([hasattr(province, key) and getattr(province, key) == val
                   for key, val in filters.items()]):
                res[province.province_id] = province
        return res

    def get_province(self, province_id) -> Province:
        return self.state.map_state.map.locations.get(province_id)

    @country_selected
    def get_my_provinces(self, **filters) -> dict[int, Province]:
        return self.get_provinces(**filters, owner_id=self.player_id)

    def get_my_cities(self, **filters) -> dict[int, Province]:
        return {**self.get_my_provinces(**filters, province_state_id=ProvinceStateID.ANNEXED_CITY),
                **self.get_my_provinces(**filters, province_state_id=ProvinceStateID.MAINLAND_CITY),
                **self.get_my_provinces(**filters, province_state_id=ProvinceStateID.OCCUPIED_CITY)}

    @country_selected
    def build_upgrade(self, province_id, upgrade):

        res = self.game_api.request_province_action(province_id, UpdateProvinceAction(
            province_ids=[province_id],
            mode=ProvinceUpdateActionModes.UPGRADE,
            slot=0,
            upgrade=upgrade,
            game=self
        ).to_dict())

    @country_selected
    def cancel_construction(self, province_id):
        self.game_api.request_province_action(province_id, UpdateProvinceAction(
            province_ids=[province_id],
            mode=ProvinceUpdateActionModes.CANCEL_BUILDING,
            slot=0,
            game=self
        ).to_dict())

    @country_selected
    def cancel_mobilization(self, province_id):
        self.game_api.request_province_action(province_id, UpdateProvinceAction(
            province_ids=[province_id],
            mode=ProvinceUpdateActionModes.CANCEL_PRODUCING,
            slot=0,
            game=self
        ).to_dict())

    @country_selected
    def mobilize_unit(self, province_id, unit_type_id):
        province = self.get_province(province_id)
        targets = [special_unit for special_unit in province.properties.possible_productions
                    if special_unit.unit.unit_type_id == unit_type_id]
        if len(targets) == 0:
            return
        target = targets[0]
        self.game_api.request_province_action(province_id, UpdateProvinceAction(
            province_ids=[province_id],
            mode=ProvinceUpdateActionModes.DEPLOYMENT_TARGET,
            slot=0,
            upgrade=target,
            game=self
        ).to_dict())

    """
    ResourceState(4)
    """

    def get_player_resource_profile(self, player_id) -> ResourceProfile | None:
        return self.state.resource_state.resource_profiles.get(player_id)

    @country_selected
    def get_my_resource_profile(self) -> ResourceProfile | None:
        return self.get_player_resource_profile(self.player_id)

    @country_selected
    def get_resource_entry(self, resource_id) -> ResourceEntry | None:
        my_resource_profile = self.get_my_resource_profile()
        if my_resource_profile:
            for category in my_resource_profile.categories.values():
                if resource_id in category.resources:
                    return category.resources[resource_id]
        return None

    @country_selected
    def get_resource_amount(self, resource_id) -> float | None:
        resource = self.get_resource_entry(resource_id)
        if resource is None:
            return None
        delta = int(self.get_last_uptime().timestamp()/ 1000)  - int(resource.time_zero.timestamp()/ 1000)
        return resource.amount_zero + delta * 1000 * resource.rate

    """
    ForeignAffairsState(5)
    """

    def get_relationships(self, **filters) -> dict[Any, dict[Any, Any]]:

        return {sender_id: {receiver_id: relationship
                            for receiver_id, relationship
                            in sender.items()
                            if (receiver_id == filters.get("receiver_id")
                                if "receiver_id" in filters.keys() else True)
                            if (relationship ==
                                filters.get("relationship_type")
                                if "relationship_type" in filters.keys()
                                else True)
                            }
                for sender_id, sender
                in self.state.foreign_affairs_state.relationships.items()
                if (sender_id == filters.get("sender_id")
                    if "sender_id" in filters.keys() else True)}

    """
    ArmyState(6)
    """

    @country_selected
    def get_armies(self) -> dict[int, Army]:
        return self.state.army_state.armies

    @country_selected
    def get_my_armies(self) -> dict[int, Army]:
        return {army.id: army
                for army in self.state.army_state.armies.values()
                if army.owner_id == self.player_id}

    @country_selected
    def get_army(self, army_id: int) -> Army:
        self.state.army_state.armies.get(army_id)

    def find_path(self, army_id: int, position=Point) -> [Command]:
        # Find Path for a army in the current game to a position
        pass

    def find_path_to_province(self, army_id: int,
                              province_id: int) -> [Command]:
        # Find path for a army in the current game to a province
        pass

    @country_selected
    def command_army(army_id: int, command: list[Command]):
        pass

    """
    ModState(11)
    """

    def get_upgrade_types(self, **filters) -> dict[int, UpgradeType]:
        return {upgrade_id: upgrade
                for upgrade_id, upgrade in self.state.mod_state.upgrades.items()
                if all(getattr(upgrade, key, None) == value for key, value in filters.items())}

    def get_upgrade_type(self, upgrade_id) -> UpgradeType | None:
        return self.state.mod_state.upgrades.get(upgrade_id)

    def get_upgrade_type_by_name_and_tier(self, name, tier) -> UpgradeType | None:
        return next(iter(self.get_upgrade_types(upgrade_identifier=name, tier=tier).values()), None)

    def get_unit_types(self, **filters) -> dict[int, UnitType]:
        return {unit_type_id: unit_type
                for unit_type_id, unit_type in self.state.mod_state.unit_types.items()
                if all(getattr(unit_type, key, None) == value for key, value in filters.items())}