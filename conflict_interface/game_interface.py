from datetime import datetime
from functools import wraps
from typing import Any
from typing import Optional

from requests import Session

from conflict_interface.action_handler import ActionHandler
from conflict_interface.data_types.action import Action
from conflict_interface.data_types.army_state.army import Army
from conflict_interface.data_types.authentication import AuthDetails
from conflict_interface.data_types.custom_types import Vector
from conflict_interface.data_types.game_api_types.login_action import DEFAULT_LOGIN_ACTION
from conflict_interface.data_types.game_api_types.login_action import LoginAction
from conflict_interface.data_types.game_object import parse_game_object
from conflict_interface.data_types.game_state.game_state import GameState
from conflict_interface.data_types.map_state.map_state_enums import ProvinceStateID
from conflict_interface.data_types.map_state.province import Province
from conflict_interface.data_types.mod_state.unit_type import UnitType
from conflict_interface.data_types.mod_state.upgrade_type import UpgradeType
from conflict_interface.data_types.newspaper_state.article import Article
from conflict_interface.data_types.player_state.faction import Faction
from conflict_interface.data_types.player_state.player_profile import PlayerProfile
from conflict_interface.data_types.player_state.team_profile import TeamProfile
from conflict_interface.data_types.research_state.research_type import ResearchType
from conflict_interface.data_types.resource_state.resource_entry import ResourceEntry
from conflict_interface.data_types.resource_state.resource_profile import ResourceProfile
from conflict_interface.data_types.resource_state.resource_state_enums import ResourceType
from conflict_interface.data_types.static_map_data import StaticMapData
from conflict_interface.game_api import GameApi
from conflict_interface.logger_config import get_logger
from conflict_interface.utils.exceptions import CountryUnselectedException
from conflict_interface.utils.exceptions import GameActivationErrorCodes
from conflict_interface.utils.exceptions import GameActivationException

logger = get_logger()

class GameInterface:
    def __init__(self, game_id: int, guest: bool, session: Session, auth_details: AuthDetails, proxy: dict = None):
        self.game_id = game_id
        self.game_api: GameApi = GameApi(session, auth_details, self.game_id, proxy=proxy)
        self.player_id = 0
        self.game_state: GameState | None = None
        self.action_handler = ActionHandler(self)
        self.guest: bool = guest

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

    def set_proxy(self, proxy: dict):
        self.game_api.set_proxy(proxy)

    def unset_proxy(self):
        self.game_api.unset_proxy()

    def load_game(self):
        """
        Join a game session as a player or a guest and set up the game state and map data.

        If the user is not joining as a guest, an attempt is made to activate the game session
        with the player's ID and team ID. If game activation fails with an error due to country
        selection, the function proceeds to update the game state. Otherwise, the game state
        is updated directly for guest users. Additionally, static map data for the game is
        retrieved and set for the current map.

        Raises:
            GameActivationException: If the game activation fails due to reasons other than
                requested country selection and the user is not a guest.
        """
        self.game_api.load_game_site()
        if self.guest:
            self.game_state = self.action_handler.create_game_state_action(use_queue=False)
        else:
            try:
                self.player_id = self.action_handler.activate_game(
                    os=self.game_api.device_details.os,
                    device=self.game_api.device_details.device,
                    selected_player_id=-1,
                    selected_team_id=-1,
                    random_team_country_selection=False,
                )
                logger.debug(f"Loading game with player id: {self.player_id}")
                login_action: LoginAction = DEFAULT_LOGIN_ACTION
                login_action.system_information.client_version = self.game_api.client_version
                login_action.system_information.os_name = self.game_api.device_details.os
                self.do_action(DEFAULT_LOGIN_ACTION, execute_immediately=True)
            except GameActivationException as e:
                if e.error_code != GameActivationErrorCodes.COUNTRY_SELECTION_REQUESTED:
                    raise e

                self.game_state = self.action_handler.create_game_state_action(use_queue=False)

        static_map_data = parse_game_object(StaticMapData, self.game_api.get_static_map_data(), self)

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
        self.player_id = self.action_handler.activate_game(self.game_api.device_details.os,
                                                           self.game_api.device_details.device,
                                                           country_id, team_id, random_country_team)
        self.do_action(DEFAULT_LOGIN_ACTION, execute_immediately=True)

    def update(self):
        """
        Updates the current state of the game by requesting the latest information
        from the game API. Integrates new data into the existing state and returns
        the updated state.

        Returns:
            States: The updated current state of the game.
        """
        # Execute any queued actions
        self.action_handler.create_game_state_action()

    """
    Utility functions
    """
    def get_api(self) -> GameApi:
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

    """
    ActionHandler related functions
    """

    def do_action(self,action: Action, execute_immediately=False):
        """
        Uses the action handler to execute an action immediately or queue it for later.
        Queuing is done to reduce the load on the server by only sending requests bundeld together roughly every 5 minutes.

        :param action: The action to be executed
        :param execute_immediately: Whether the action should be executed immediately or queued defaults to False

        :returns: The response from the server
        """
        if execute_immediately:
            game_state, action_uid = self.action_handler.immediate_action(action)
            if self.game_state:
                self.game_state.update(game_state)
            else:
                self.game_state = game_state
            return action_uid
        else:
            return self.action_handler.que_action(action)


    def get_action_results(self) -> dict[int, int]:
        return self.action_handler.get_action_results()

    """
    PlayerState(1)
    """

    def is_country_selected(self) -> bool:
        return self.player_id != 0

    def get_player(self, player_id) -> PlayerProfile | None:
        return self.game_state.states.player_state.players.get(player_id)

    def get_my_player(self) -> PlayerProfile:
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

    def get_current_articles(self) -> Vector[Article]:
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

    def get_provinces_by_name(self, name) -> Optional[Province]:
        province = self.get_provinces(name=name)
        if province:
            return next(iter(province.values()))
        else:
            return None

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
    def get_resource_entry(self, resource_id: ResourceType) -> ResourceEntry | None:
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
    def get_armies(self, **filters) -> dict[int, Army]:
        return {
            army_id: army
            for army_id, army in self.game_state.states.army_state.armies.items()
            if all(getattr(army, key) == value for key, value in filters.items())
        }

    @country_selected
    def get_my_armies(self, **filters) -> dict[int, Army]:
        return self.get_armies(owner_id=self.player_id, **filters)

    @country_selected
    def get_army(self, army_id: int) -> Army:
        return self.game_state.states.army_state.armies.get(army_id)

    @country_selected
    def get_army_by_number(self, army_number: int) -> Army:
        return next(iter(self.get_my_armies(army_number=army_number).values()), None)
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

    def get_unit_type(self, unit_type_id: int) -> UnitType | None:
        return self.game_state.states.mod_state.all_unit_types.get(unit_type_id)

    def get_unit_types(self, **filters) -> dict[int, UnitType]:
        return {unit_type_id: unit_type
                for unit_type_id, unit_type in self.game_state.states.mod_state.all_unit_types.items()
                if all(getattr(unit_type, key, None) == value for key, value in filters.items())}

    def get_unit_type_by_name_and_tier(self, name, tier, faction: Faction = None) -> UnitType | None:
        if faction is None:
            faction = self.get_my_player().faction
        candidates = self.get_unit_types(type_name=name, tier=tier)
        for candidate in candidates.values():
            if candidate.has_faction(faction):
                return candidate
        return None

    def get_research_type(self, research_id) -> ResearchType | None:
        return self.game_state.states.mod_state.research_types.get(research_id)

    def get_research_types(self, **filters) -> dict[int, ResearchType]:
        return {research_id: research_type
                for research_id, research_type in self.game_state.states.mod_state.research_types.items()
                if all(getattr(research_type, key, None) == value for key, value in filters.items())}

    def get_research_type_by_name_and_tier(self, name, tier, faction: Faction = None) -> ResearchType | None:
        if faction is None:
            faction = self.get_my_player().faction

        for research_id, research_type in self.get_research_types().items():
            if research_type.name.endswith(faction.code):
                if research_type.name == name + " " + faction.code:
                    return research_type
            else:
                if research_type.name == name:
                    return research_type