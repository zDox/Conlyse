from collections.abc import Callable
from datetime import datetime
from functools import wraps
from symtable import Function
from typing import Optional

from requests import Session

from conflict_interface.action_handler import ActionHandler
from conflict_interface.data_types.action import Action
from conflict_interface.data_types.army_state.army import Army
from conflict_interface.data_types.authentication import AuthDetails
from conflict_interface.data_types.foreign_affairs_state.foreign_affairs_state_enums import ForeignAffairRelationTypes
from conflict_interface.data_types.game_api_types.login_action import DEFAULT_LOGIN_ACTION
from conflict_interface.data_types.game_api_types.login_action import LoginAction
from conflict_interface.data_types.game_event_state.game_event import GameEvent
from conflict_interface.data_types.game_object import parse_game_object
from conflict_interface.data_types.game_state.game_state import GameState
from conflict_interface.data_types.map_state.map import ProvinceType
from conflict_interface.data_types.map_state.map_state_enums import ProvinceStateID
from conflict_interface.data_types.mod_state.unit_type import UnitType
from conflict_interface.data_types.mod_state.upgrade_type import UpgradeType
from conflict_interface.data_types.newspaper_state.article import Article
from conflict_interface.data_types.player_state.faction import Faction
from conflict_interface.data_types.player_state.player_profile import PlayerProfile
from conflict_interface.data_types.player_state.team_profile import TeamProfile
from conflict_interface.data_types.research_state.research_state import ResearchState
from conflict_interface.data_types.research_state.research_type import ResearchType
from conflict_interface.data_types.research_state.reserach import Research
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
        self.game_event_handler: Callable = self.default_event_handler



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
        self.player_id = self.action_handler.activate_game(os=self.game_api.device_details.os,
                                                           device=self.game_api.device_details.device,
                                                           selected_player_id=country_id,
                                                           selected_team_id=team_id,
                                                           random_team_country_selection=random_country_team)
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
        Retrieves the current client time adjusted for the game's timescale.

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
        Queuing is done to reduce the load on the server by only sending requests bundled together roughly every 5 minutes.

        :param action: The action to be executed
        :param execute_immediately: Whether the action should be executed immediately or queued defaults to False

        :returns: The response from the server
        """
        if execute_immediately:
            game_state, action_uid = self.action_handler.immediate_action(action)
            if not self.game_state:
                self.game_state = game_state
            return action_uid
        else:
            return self.action_handler.que_action(action)


    def get_action_results(self) -> dict[int, int]:
        return self.action_handler.get_action_results()

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
    ForeignAffairsState(5)
    """
    def get_relation(self, sender_id: int, receiver_id: int) -> ForeignAffairRelationTypes:
        return self.game_state.states.foreign_affairs_state.relations.get_relation(sender_id, receiver_id)


    """
    GameEventState(24)
    """
    @country_selected
    def get_game_events(self) -> list[GameEvent]:
        return list(self.game_state.states.game_event_state.game_events)


    """
    MapState(3)
    """
    def get_map(self):
        return self.game_state.states.map_state.map

    def get_province(self, province_id: int) -> ProvinceType:
        return self.game_state.states.map_state.map.provinces.get(province_id)

    def get_provinces(self, **filters) -> dict[int, ProvinceType]:
        res = {}
        for province in self.game_state.states.map_state.map.provinces.values():
            if all([hasattr(province, key) and getattr(province, key) == val
                    for key, val in filters.items()]):
                res[province.id] = province
        return res

    def get_provinces_by_name(self, name) -> Optional[ProvinceType]:
        province = self.get_provinces(name=name)
        if province:
            return next(iter(province.values()))
        else:
            return None

    @country_selected
    def get_my_provinces(self, **filters) -> dict[int, ProvinceType]:
        return self.get_provinces(**filters, owner_id=self.player_id)

    @country_selected
    def get_my_cities(self, **filters) -> dict[int, ProvinceType]:
        return {**self.get_my_provinces(**filters, province_state_id=ProvinceStateID.ANNEXED_CITY),
                **self.get_my_provinces(**filters, province_state_id=ProvinceStateID.MAINLAND_CITY),
                **self.get_my_provinces(**filters, province_state_id=ProvinceStateID.OCCUPIED_CITY)}


    """
    ModState(11)
    """
    def get_upgrade_types(self, **filters) -> dict[int, UpgradeType]:
        """
        Filters and retrieves specific upgrade types from the game state based on provided criteria.

        Args:
            **filters: Arbitrary keyword arguments specifying filter conditions. Each argument
                should correspond to an attribute of `UpgradeType` to filter by and the value
                it must match.

        Returns:
            dict[int, UpgradeType]: A dictionary where keys are upgrade IDs (integers) and
            values are `UpgradeType` instances that satisfy the given filter criteria.
        """
        return {upgrade_id: upgrade
                for upgrade_id, upgrade in self.game_state.states.mod_state.upgrades.items()
                if all(getattr(upgrade, key, None) == value for key, value in filters.items())}

    def get_upgrade_type(self, upgrade_id) -> UpgradeType | None:
        """
        Provides functionality to retrieve the type of upgrade corresponding
        to a given upgrade id.

        Parameters:
        upgrade_id : int
            A unique identifier for the specific upgrade to be retrieved.

        Returns:
        UpgradeType | None
            The upgrade type object corresponding to the provided upgrade
            ID, or None if no matching upgrade is found.
        """
        return self.game_state.states.mod_state.upgrades.get(upgrade_id)

    def get_upgrade_type_by_name_and_tier(self, name, tier) -> UpgradeType | None:
        """
        Determines the upgrade type based on the given name and tier.

        Parameters:
            name (str): The name of the upgrade to search for.
            tier (int): The tier level of the upgrade to search for.

        Returns:
            UpgradeType | None: Returns an UpgradeType object if a match is found;
            otherwise, None.
        """
        return next(iter(self.get_upgrade_types(upgrade_identifier=name, tier=tier).values()), None)

    def get_unit_type(self, unit_type_id: int) -> UnitType | None:
        """
        Retrieves the unit type corresponding to the given unit type id.

        Parameters:
            unit_type_id (int): The id of the unit type to retrieve.

        Returns:
            UnitType | None: An instance of UnitType if the given unit_type_id exists
            in the collection of all unit types; otherwise, None.
        """
        return self.game_state.states.mod_state.all_unit_types.get(unit_type_id)

    def get_unit_types(self, **filters) -> dict[int, UnitType]:
        """
        Filters and retrieves unit types based on the specified criteria.

        Args:
            filters: Arbitrary keyword arguments representing the filtering criteria. ach argument
                should correspond to an attribute of `UnitType` to filter by and the value
                it must match.

        Returns:
            dict[int, UnitType]: A dictionary mapping unit type IDs (int) to their corresponding
            UnitType objects that match the specified filters.
        """
        return {unit_type_id: unit_type
                for unit_type_id, unit_type in self.game_state.states.mod_state.all_unit_types.items()
                if all(getattr(unit_type, key, None) == value for key, value in filters.items())}

    def get_unit_type_by_name_and_tier(self, name, tier, faction: Faction = None) -> UnitType | None:
        """
        Retrieves a UnitType based on the provided unit name, tier, and optionally
        faction. If the faction is not provided, the current player's faction will be used
        for the lookup. The function searches through candidates matching the name and tier
        and returns the first one that belongs to the specified faction.

        Parameters:
            name (str): The name of the unit type to search for.
            tier (int): The tier level of the unit type to search for.
            faction (Optional[Faction]): The faction to match against. Defaults to the faction of the current
                                        player if not provided.

        Returns:
            UnitType | None : The first unit type matching the specified name, tier, and faction,
                            or None if no match is found.
        """
        if faction is None:
            faction = self.get_my_player().faction
        candidates = self.get_unit_types(type_name=name, tier=tier)
        for candidate in candidates.values():
            if candidate.has_faction(faction):
                return candidate
        return None

    def get_research_type(self, research_id) -> ResearchType | None:
        """
        Gets the type of research corresponding to the given research ID. If the
        research ID does not exist in the current research types, returns None.

        Parameters:
            research_id: The identifier of the research.

        Returns:
            ResearchType: The type of research mapped to the given ID, if found.
            None: If no research type is associated with the provided ID.
        """
        return self.game_state.states.mod_state.research_types.get(research_id)

    def get_research_types(self, **filters) -> dict[int, ResearchType]:
        """
        Fetch research types from the game state based on specified filters.

        Parameters:
            **filters (dict): Keyword arguments representing the filters to apply. Each key should
                correspond to an attribute of `ResearchType`, and the value specifies
                the required value for that attribute.

        Returns:
            dict[int, ResearchType]: A dictionary mapping research IDs to `ResearchType` instances
                that satisfy all the specified filters.
        """
        return {research_id: research_type
                for research_id, research_type in self.game_state.states.mod_state.research_types.items()
                if all(getattr(research_type, key, None) == value for key, value in filters.items())}

    def get_research_type_by_name_and_tier(self, name, tier, faction: Faction = None) -> ResearchType | None:
        """
        Finds a research type by its name and tier, and optionally filters by faction.

        This method traverses the available research types, looking for a match
        on the given name and tier. If a faction is provided, it checks for the
        faction-specific code in the research type's name. If no faction is
        provided, the faction of the current player is used. Returns the
        matching research type if found, otherwise returns None.

        Parameters:
            name (str): The name of the research type to find.
            tier (int): The tier of the research type to find.
            faction (Optional[Faction]): The faction to filter the research types on. If not provided, the
                faction is determined from the current player's faction.

        Returns:
            ResearchType | None:
                The research type object matching the criteria, or None if no match
                is found.
        """
        if faction is None:
            faction = self.get_my_player().faction

        for research_id, research_type in self.get_research_types().items():
            if research_type.name.endswith(faction.code):
                if research_type.name == name + " " + faction.code and research_type.tier == tier:
                    return research_type
            else:
                if research_type.name == name and research_type.tier == tier:
                    return research_type

    """
    NewspaperState(2)
    """
    def get_current_articles(self) -> list[Article]:
        return list(self.game_state.states.newspaper_state.articles)


    """
    PlayerState(1)
    """
    def is_country_selected(self) -> bool:
        """
        Determines if a country is selected in the current game.

        Returns:
            bool: True if a country is selected, False otherwise.
        """
        return self.player_id != 0

    def get_player(self, player_id) -> PlayerProfile | None:
        """
        Returns the profile of the player with the given ID.

        Parameters:
            player_id (int): The unique identifier of the player whose profile is to
                be returned.

        Returns:
            PlayerProfile | None: The profile of the player if found; otherwise, None.
        """
        return self.game_state.states.player_state.players.get(player_id)

    def get_my_player(self) -> PlayerProfile | None:
        """
        Returns the profile of the current player.

        Returns:
            PlayerProfile | None: The profile of the current player if a player is selected; else None.
        """
        return self.get_player(self.player_id)


    def get_players(self, **filters) -> dict[int, PlayerProfile]:
        """
        Filters player profiles based on provided criteria and returns them.

        Parameters:
            filters: dict
                Keyword arguments representing the criteria used to filter the player
                profiles. Each key in this dictionary corresponds to an attribute of
                a `PlayerProfile`, and the associated value represents the value that
                attribute must match for the player profile to be included in the
                result.

        Returns:
            dict[int, PlayerProfile]
                A dictionary where the keys are player IDs and the values are the
                corresponding PlayerProfile objects that meet the filter criteria.
        """
        return {player.player_id: player
                for player in self.game_state.states.player_state.players.values()
                if all([getattr(player, key) == val
                        for key, val in filters.items()])}



    def get_playable_countries(self) -> dict[int, PlayerProfile]:
        """
        Retrieves a dictionary of playable countries and their associated player profiles.

        Returns
            dict[int, PlayerProfile]:
                A dictionary where the key is an integer representing the country ID, and the
                value is an associated `PlayerProfile` containing details about the player.
        """
        return self.get_players(available=True)

    def get_human_players(self) -> dict[int, PlayerProfile]:
        """
        Retrieves a dictionary of all countries that are played by humans and their associated player profiles.


        Returns:
            dict[int, PlayerProfile]: A dictionary where the keys are the player IDs
            and the values are the corresponding PlayerProfile instances for human
            players.
        """
        return self.get_players(computer_player=False)

    def get_teams(self, **filters) -> dict[int, TeamProfile]:
        """
        Returns a dictionary of team profiles, filtered based on the provided criteria.

        Parameters:
            filters:
                Keyword arguments representing the criteria used to filter the team
                profiles. Each key in this dictionary corresponds to an attribute of
                a `TeamProfile`, and the associated value represents the value that
                attribute must match for the team profile to be included in the
                result.

        Returns:
            dict[int, TeamProfile]: A dictionary where the keys are `team_id` values
                and the values are the corresponding `TeamProfile` objects that satisfy
                all the provided filters.
        """
        return {team.team_id: team
                for team in self.game_state.states.player_state.teams.values()
                if all(getattr(team, key) == val for key, val in filters.items())}

    def get_team(self, team_id) -> TeamProfile | None:
        """
        Returns team profile for the specified team ID.

        Parameters:
            team_id: The identifier of the team to retrieve.

        Returns:
            TeamProfile: The profile of the team if found.
            None: If the team ID does not exist in the game state.
        """
        return self.game_state.states.player_state.teams.get(team_id)


    """
    ResearchState(23)
    """
    def get_research_state(self) -> ResearchState:
        return self.game_state.states.research_state

    def get_current_research(self) -> list[Research]:
        """
        Gets the list of active research currently being researched in the game.

        Returns:
            list[Research]: A list of Research objects currently being researched in
            the game.
        """
        return list(self.game_state.states.research_state.current_researches)

    def get_completed_research(self) -> dict[int, Research]:
        """
        Retrieves the completed research data from the game state.

        Returns:
            HashMap[int, Research]: A dictionary  where keys are integers
            representing research IDs, and values are `Research` objects containing
            details about each completed research.
        """
        return dict(self.game_state.states.research_state.completed_researches)

    """
    ResourceState(4)
    """
    @country_selected
    def is_affordable(self, cost: dict[ResourceType, int]):
        """
        Determines if the cost of resources can be afforded given the current
        available resources.

        Parameters:
            cost: dict[ResourceType, int]
                A dictionary representing the cost of resources where the key
                is the resource type and the value is the required amount.

        Returns:
            bool: Returns True if the available resources are sufficient to cover
                the cost; otherwise, returns False.
        """
        return self.get_my_resource_profile().is_affordable(cost)

    @country_selected
    def get_my_resource_amounts(self) -> dict[ResourceType, int]:
        """
        Computes the current amount of each resource type.
        Returns them in a dictionary.

        Returns:
            dict[ResourceType, int]: A dictionary mapping each resource
            type to its amount.
        """
        return self.get_my_resource_profile().get_resource_amounts()

    def get_player_resource_profile(self, player_id) -> ResourceProfile | None:
        return self.game_state.states.resource_state.resource_profiles.get(player_id)

    @country_selected
    def get_my_resource_profile(self) -> ResourceProfile:
        """

        """
        return self.get_player_resource_profile(self.player_id)

    @country_selected
    def get_resource_entry(self, resource_id: ResourceType) -> ResourceEntry | None:
        return self.get_my_resource_profile().get_resource_entry(resource_id)

    """
    Event Handler
    """

    def default_event_handler(self, game_interface):
        pass

    def set_event_handler(self, event_handler: Callable):
        self.game_event_handler = event_handler