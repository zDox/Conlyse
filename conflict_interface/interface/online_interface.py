from __future__ import annotations

import os.path
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from time import time
from typing import Callable
from typing import TYPE_CHECKING
from typing import override

from cloudscraper25 import CloudScraper

from conflict_interface.data_types.newest.action_handler import ActionHandler

from conflict_interface.api.game_api import GameApi
from conflict_interface.game_object.game_object import GameObject
from conflict_interface.game_object.game_object_parse_json import JsonParser
from conflict_interface.interface.game_interface import GameInterface
from conflict_interface.logger_config import get_logger
from conflict_interface.replay.make_bipatch_between_gamestates import make_bireplay_patch
from conflict_interface.replay.replaysegment import ReplaySegment
from conflict_interface.replay.replay_patch import BidirectionalReplayPatch
from conflict_interface.utils.exceptions import GameActivationErrorCodes
from conflict_interface.utils.exceptions import GameActivationException
# Online Interface must use newest datatypes (trivially)
from conflict_interface.data_types.newest.static_map_data import StaticMapData

if TYPE_CHECKING:
    from conflict_interface.data_types.newest.action import Action
    from conflict_interface.api.authentication import AuthDetails
    from conflict_interface.data_types.newest.game_api_types.login_action import LoginAction


logger = get_logger()

class OnlineInterface(GameInterface):
    def __init__(self, version: int, game_id: int,
                 session: CloudScraper,
                 auth_details: AuthDetails,
                 login_action: LoginAction,
                 guest: bool = False,
                 proxy: dict = None,
                 replay_filepath: str = None):
        super().__init__()
        self.replay: ReplaySegment | None = None
        self.game_id = game_id
        self.game_api: GameApi = GameApi(session, auth_details, self.game_id, proxy=proxy)
        self.game_event_handler: Callable = self.default_event_handler
        self.guest: bool = guest
        self.action_handler = ActionHandler(self)
        self.static_map_data = None
        self.version = version
        self.parser = JsonParser(version)
        self.parser.type_graph.build_graph()
        self.loging_action = login_action

        self.replay_filepath = replay_filepath

    def _handle_replay_init(self, static_map_data: StaticMapData):
        if not os.path.exists(self.replay_filepath):
            self.replay = ReplaySegment(file_path=Path(self.replay_filepath), mode="w", game_id=self.game_id, player_id=self.player_id, max_patches=400)
            self.replay.open()
            self.replay.record_initial_game_state(
                                time_stamp = self.client_time(),
                                game_id = self.game_id,
                                player_id = self.player_id,
                                game_state = self.game_state)
            self.replay.record_static_map_data(
                                game_id = self.game_id,
                                player_id = self.player_id,
                                static_map_data = static_map_data)
        else:
            self.replay = ReplaySegment(file_path=Path(self.replay_filepath), mode="a", game_id=self.game_id, player_id=self.player_id)
            self.replay.open()
            last_game_state = self.replay.get_last_game_state()
            replay_patch = make_bireplay_patch(last_game_state, self.game_state)
            self.replay.append_patches(
                time_stamp=self.client_time(),
                game_id=self.game_id,
                player_id=self.player_id,
                replay_patches=[replay_patch],
                game=self
            )
        GameObject.set_game_recursive(self.game_state, None)
        self.replay.set_last_game_state(self.game_state)
        self.replay.close()
        GameObject.set_game_recursive(self.game_state, self)


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
                login_action: LoginAction = deepcopy(self.loging_action)
                login_action.system_information.client_version = self.game_api.client_version
                login_action.system_information.os_name = self.game_api.device_details.os
                self.do_action(self.loging_action, execute_immediately=True)
            except GameActivationException as e:
                if e.error_code != GameActivationErrorCodes.COUNTRY_SELECTION_REQUESTED:
                    raise e

                self.game_state = self.action_handler.create_game_state_action(use_queue=False, send_state_ids=False)

        json_static_map_data = self.game_api.get_static_map_data()
        self.static_map_data = self.parser.parse_any(StaticMapData, json_static_map_data, self)

        if self.replay_filepath:
            self._handle_replay_init(self.static_map_data)

        self.game_state.states.map_state.map.set_static_map_data(self.static_map_data)

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
        self.game_state = None
        self.action_handler.game_state = None
        self.do_action(self.loging_action, execute_immediately=True)
        self.game_state.states.map_state.map.set_static_map_data(self.static_map_data)

    def update(self):
        """
        Updates the current state of the game by requesting the latest information
        from the game API. Integrates new data into the existing state and returns
        the updated state.

        Returns:
            States: The updated current state of the game.
        """
        # Execute any queued actions
        t1 = time()
        self.action_handler.create_game_state_action()
        logger.debug(f"Update took: {time() - t1}")

    """
    Everything regarding replay capabilities
    """
    def is_recording(self) -> bool:
        return self.replay is not None

    def record_patch(self, rp: BidirectionalReplayPatch):
        if self.is_recording():
            self.replay = ReplaySegment(file_path=Path(self.replay_filepath), mode="a", game_id=self.game_id, player_id=self.player_id)
            self.replay.open()
            self.replay.append_patches(
                time_stamp=self.client_time(),
                game_id=self.game_id,
                player_id=self.player_id,
                replay_patches=[rp],
                game=self)
            GameObject.set_game_recursive(self.game_state, None)
            self.replay.set_last_game_state(self.game_state)
            self.replay.close()
            GameObject.set_game_recursive(self.game_state, self)

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