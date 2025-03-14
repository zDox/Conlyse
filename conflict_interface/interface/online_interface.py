from datetime import datetime
from typing import Callable
from typing import override

from requests import Session

from conflict_interface.action_handler import ActionHandler
from conflict_interface.data_types.action import Action
from conflict_interface.data_types.authentication import AuthDetails
from conflict_interface.data_types.game_api_types.login_action import DEFAULT_LOGIN_ACTION
from conflict_interface.data_types.game_api_types.login_action import LoginAction
from conflict_interface.data_types.game_object import parse_game_object
from conflict_interface.data_types.static_map_data import StaticMapData
from conflict_interface.game_api import GameApi
from conflict_interface.interface.game_interface import GameInterface
from conflict_interface.logger_config import get_logger
from conflict_interface.utils.exceptions import GameActivationErrorCodes
from conflict_interface.utils.exceptions import GameActivationException

logger = get_logger()

class OnlineInterface(GameInterface):
    def __init__(self, game_id: int, session: Session, auth_details: AuthDetails, guest: bool = False, proxy: dict = None):
        super().__init__(game_id=game_id)
        self.game_api: GameApi = GameApi(session, auth_details, self.game_id, proxy=proxy)
        self.game_event_handler: Callable = self.default_event_handler
        self.guest: bool = guest
        self.action_handler = ActionHandler(self)

    @override
    @property
    def online(self) -> "OnlineInterface":
        return self

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
                self.online.do_action(DEFAULT_LOGIN_ACTION, execute_immediately=True)
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
    Event Handler
    """

    def default_event_handler(self, game_interface):
        pass

    def set_event_handler(self, event_handler: Callable):
        self.game_event_handler = event_handler
