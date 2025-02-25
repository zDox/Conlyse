from __future__ import annotations

from datetime import datetime, timedelta
from functools import wraps
from typing import Any, cast

from .data_types.army_state.army import Army
from .data_types.custom_types import ArrayList
from .data_types.game_object import parse_game_object
from .data_types.map_state import Province, ProvinceStateID
from .data_types.mod_state import UpgradeType, UnitType
from .data_types.newspaper_state import Article
from .data_types.player_state import PlayerProfile
from .data_types.resource_state import ResourceProfile, ResourceEntry
from .data_types.static_map_data import StaticMapData
from .game_api import GameAPI
from .data_types.game_state import GameState
from .utils.exceptions import CountryUnselectedException, GameActivationException, GameActivationErrorCodes

from conflict_interface.data_types.player_state.team_profile import TeamProfile



class GameInterface:
    def __init__(self, game_id: int, game_api: GameAPI):
        self.game_api = game_api
        self.game_id = game_id
        self.player_id = 0
        self.game_state: GameState | None = None

    @staticmethod
    def country_selected(func):
        """
        Decorator function to ensure a country is selected before executing the wrapped function.

        Only allows the execution of the wrapped function if `is_country_selected` returns True.
        If no country is selected, raises a CountryUnselectedException.

        Parameters:
            func (Callable): The function to be wrapped by the decorator.

        Returns:
            Callable: The wrapped function that enforces the country selection check.
        """

        @wraps(func)
        def wrap(self, *args, **kwargs):
            if self.is_country_selected():
                return func(self, *args, **kwargs)
            else:
                raise CountryUnselectedException("Country not selected.")

        return wrap

    def join_game(self, guest=False):
        """
        Join a game session as a player or a guest and set up the game state and map data.

        If the user is not joining as a guest, an attempt is made to activate the game session
        with the player's ID and team ID. If game activation fails with an error due to country
        selection, the function proceeds to update the game state. Otherwise, the game state
        is updated directly for guest users. Additionally, static map data for the game is
        retrieved and set for the current map.

        Args:
            guest (bool): Optional; True if the user is joining as a guest, False otherwise.
                Defaults to False.

        Raises:
            GameActivationException: If the game activation fails due to reasons other than
                requested country selection and the user is not a guest.
        """
        self.game_api.load_game_site()
        if not guest:
            try:
                self.player_id = self.game_api.request_game_activation(
                    selected_player_id=-1,
                    selected_team_id=-1,
                    random_team_country_selection=False,
                )

                self.game_state = parse_game_object(GameState, self.game_api.request_login_action(), self)
            except GameActivationException as e:
                if e.error_code != GameActivationErrorCodes.COUNTRY_SELECTION_REQUESTED:
                    raise e

                self.game_state = parse_game_object(GameState, self.game_api.request_game_update(), self)
        else:
            self.game_state = parse_game_object(GameState, self.game_api.request_game_update(), self)
        static_map_data = parse_game_object(StaticMapData, self.game_api.get_static_map_data(), self)


        self.game_state = cast(GameState, self.game_state)
        print(type(self.game_state))
        self.game_state.states.map_state.map.set_static_map_data(static_map_data)

    def select_country(self, country_id=-1, team_id=-1,
                       random_country_team=False):
        """
        Selects a country for the player based on the provided parameters or randomly
        if specified. Assigns the player ID from the game API, activates the game,
        and sets the current state based on the API response.

        Args:
            country_id (int, optional): Identifier for the desired country. Defaults
                to -1, indicating no specific country has been selected.
            team_id (int, optional): Identifier for the desired team. Defaults
                to -1, indicating no specific team has been selected.
            random_country_team (bool, optional): Flag indicating whether to select
                a country and team randomly. Defaults to False.

        Raises:
            None

        Returns:
            None
        """
        self.player_id = self.game_api.request_game_activation(country_id, team_id,
                                              random_country_team)

        self.game_state = parse_game_object(GameState, self.game_api.request_login_action(), self)

    def update(self) -> GameState:
        """
        Updates the current state of the game by requesting the latest information
        from the game API. Integrates new data into the existing state and returns
        the updated state.

        Returns:
            States: The updated current state of the game.
        """
        new_states = self.game_api.request_game_update()
        self.game_state.states.update(new_states)
        return self.game_state

    """
    Utility functions
    """
    def get_api(self) -> GameAPI:
        return self.game_api

    def client_time(self) -> datetime:
        """
        Retrieves the current client time adjusted for the game's time scale.

        Returns
        -------
        datetime
            The adjusted client time as a datetime object.
        """
        return self.game_api.client_time(self.game_state.states.game_info_state.time_scale)


    def get_latest_uptime(self) -> datetime:
        """
        Retrieves the most recent uptime as a datetime object. This method converts
        timestamps stored as strings in the game API's timestamp data structure to
        datetime objects and determines the most recent one. Non-relevant entries,
        such as "java.util.HashMap", are excluded during processing.

        Returns
        -------
        datetime
            The latest datetime object created from the provided timestamps.
        """
        update_times = [datetime.fromtimestamp(int(time_stamp_str) / 1000)
                        for time_stamp_str in self.game_api.time_stamps.values()
                        if time_stamp_str != "java.util.HashMap"]
        return max(update_times)



    """
    PlayerState(1)
    """

    def is_country_selected(self) -> bool:
        return self.player_id != 0

    def get_player(self, player_id) -> PlayerProfile | None:
        return self.game_state.states.player_state.players.get(player_id)

    def get_my_player(self):
        return self.get_player(self.player_id)

    def get_players(self, **filters) -> dict[int, PlayerProfile]:
        return {player.player_id: player
                for player in self.game_state.states.player_state.players.values()
                if all([getattr(player, key) == val
                        for key, val in filters.items()])}

    def get_playable_countries(self) -> dict[int, PlayerProfile]:
        return self.get_players(available=True)

    def get_human_players(self) -> dict[int, PlayerProfile]:
        return self.get_players(computer_player=False)

    def get_teams(self, **filters) -> dict[int, TeamProfile]:
        return {team.team_id: team
                for team in self.game_state.states.player_state.teams.values()
                if all(getattr(team, key) == val for key, val in filters.items())}

    def get_team(self, team_id) -> TeamProfile | None:
        return self.game_state.states.player_state.teams.get(team_id)

    """
    NewspaperState(2)
    """

    def get_articles(self, day) -> dict[int, Article]:
        return {article_id: article
                for article_id, article in self.game_state.states.newspaper_state.articles
                if self.relative_time_since_start(article.time_stamp).days + 1 == day}

    def get_current_articles(self) -> ArrayList[Article]:
        return self.game_state.states.newspaper_state.articles

    """
    MapState(3)
    """

    def get_provinces(self, **filters) -> dict[int, Province]:
        res = {}
        for province in self.game_state.states.map_state.map.locations:
            if all([hasattr(province, key) and getattr(province, key) == val
                   for key, val in filters.items()]):
                res[province.province_id] = province
        return res

    # TODO fix (changed to HashSet)
    def get_province(self, province_id) -> Province:
        return self.game_state.states.map_state.map.locations.get(province_id)

    @country_selected
    def get_my_provinces(self, **filters) -> dict[int, Province]:
        return self.get_provinces(**filters, owner_id=self.player_id)

    def get_my_cities(self, **filters) -> dict[int, Province]:
        return {**self.get_my_provinces(**filters, province_state_id=ProvinceStateID.ANNEXED_CITY),
                **self.get_my_provinces(**filters, province_state_id=ProvinceStateID.MAINLAND_CITY),
                **self.get_my_provinces(**filters, province_state_id=ProvinceStateID.OCCUPIED_CITY)}

    """
    ResourceState(4)
    """

    def get_player_resource_profile(self, player_id) -> ResourceProfile | None:
        return self.game_state.states.resource_state.resource_profiles.get(player_id)

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
                in self.game_state.states.foreign_affairs_state.relationships.items()
                if (sender_id == filters.get("sender_id")
                    if "sender_id" in filters.keys() else True)}

    """
    ArmyState(6)
    """

    @country_selected
    def get_armies(self) -> dict[int, Army]:
        return self.game_state.states.army_state.armies

    @country_selected
    def get_my_armies(self) -> dict[int, Army]:
        return {army.id: army
                for army in self.game_state.states.army_state.armies.values()
                if army.owner_id == self.player_id}

    @country_selected
    def get_army(self, army_id: int) -> Army:
        return self.game_state.states.army_state.armies.get(army_id)

    """
    ModState(11)
    """

    def get_upgrade_types(self, **filters) -> dict[int, UpgradeType]:
        return {upgrade_id: upgrade
                for upgrade_id, upgrade in self.game_state.states.mod_state.upgrades.items()
                if all(getattr(upgrade, key, None) == value for key, value in filters.items())}

    def get_upgrade_type(self, upgrade_id) -> UpgradeType | None:
        return self.game_state.states.mod_state.upgrades.get(upgrade_id)

    def get_upgrade_type_by_name_and_tier(self, name, tier) -> UpgradeType | None:
        return next(iter(self.get_upgrade_types(upgrade_identifier=name, tier=tier).values()), None)

    def get_unit_types(self, **filters) -> dict[int, UnitType]:
        return {unit_type_id: unit_type
                for unit_type_id, unit_type in self.game_state.states.mod_state.unit_types.items()
                if all(getattr(unit_type, key, None) == value for key, value in filters.items())}