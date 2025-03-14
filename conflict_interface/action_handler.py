from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from conflict_interface.data_types.action import Action
from conflict_interface.data_types.custom_types import LinkedList
from conflict_interface.data_types.game_api_types.game_activation_action import GameActivationAction
from conflict_interface.data_types.game_api_types.game_state_action import GameStateAction
from conflict_interface.data_types.game_object import dump_any
from conflict_interface.data_types.game_object import parse_game_object
from conflict_interface.data_types.game_state.game_state import GameState
from conflict_interface.game_api import GameApi

from conflict_interface.logger_config import get_logger
from conflict_interface.utils.bidict import Bidict
from conflict_interface.utils.exceptions import GameActivationException

if TYPE_CHECKING:
    from conflict_interface.interface.online_interface import OnlineInterface

logger = get_logger()


class ActionHandler:
    """
    Class to handle all types of actions in the game. and Hub
    It acts as the middleman between the game or hub interface and the game api

    We differentiate between major and minor actions:
    Major actions are actions that are sent directly to the game server
    Minor actions are actions that are sent in a major action request
    Those are mainly actions that influence the game state which can be added to the que
    and will be sent in one game state action

    There are two types of major actions:
    1. GameStateAction: This action is used to send multiple state update actions in one request
    2. Activate Game: This action is used to activate the game which is done on join

    The class also has a que_action method to add actions to the que

    :ivar queue: A list of minor actions to be executed (the que)
    :ivar action_request_id: The current action request id it is incremented for each action needed for the req
    :ivar game_api: Reference to the game api
    :ivar game: Reference to the game interface
    :ivar language: The language of the game / the requests
    :ivar game_state: Reference to the current game state if available
    :ivar action_counter: Counter for the number of actions queued or executed immediately. Used for later
                            determining the action result.
    :ivar action_request_id_to_action_uid: A bidirectional mapping between unique action IDs and their corresponding action request IDs.
    """

    def __init__(self, game: OnlineInterface):
        self.queue: list[tuple[int, Action]] = []
        self.past_actions: list[tuple[int, Action]] = []
        self.action_request_id = 0
        self.game_api: GameApi = game.get_api()
        self.game = game
        self.language = "en"  # TODO: Make this dynamic
        self.game_state: GameState | None= None
        self.action_counter = 0
        self.action_request_id_to_action_uid: Bidict[str, int] = Bidict()
        self.action_results: dict[int, int] = {}


    def que_action(self, action: Action) -> int:
        """
        Add a minor action to the action que

        :param action: The action to be added to the que

        :raises ValueError: If the action is not a subclass of Action,
                            or if the action is a GameStateAction or GameActivationAction (a major action)
        """
        if not issubclass(action.__class__, Action):
            raise ValueError(f"Action {action} is not a GameObject")
        if isinstance(action, GameStateAction):
            raise ValueError(f"GameStateAction {action} should not be added to the que but executed directly")
        if isinstance(action, GameActivationAction):
            raise ValueError(f"GameActivationAction {action} should not be added to the que but executed directly")
        action_uid = self.action_counter
        self.queue.append((action_uid, action))
        self.action_counter += 1
        return action_uid

    def immediate_action(self, action: Action) -> tuple[GameState, int]:
        """
        Execute a minor action immediately
        this is done by creating a game state action with only the provided action and executing it

        :param action: The minor game state action to be executed

        :raises ValueError: If the action is not a subclass of Action,
                            or if the action is a GameStateAction or GameActivationAction (a major action)
        """
        if not issubclass(action.__class__, Action):
            raise ValueError(f"Action {action} is not a GameObject")
        if isinstance(action, GameStateAction):
            raise ValueError(f"GameStateAction {action} should not be added to the que but executed directly")
        if isinstance(action, GameActivationAction):
            raise ValueError(f"GameActivationAction {action} should not be added to the que but executed directly")

        action_uid = self.action_counter
        self.action_counter += 1
        return self.create_game_state_action(use_queue=False, custom_actions=[(action_uid, action)]), action_uid

    def execute_action(self, action):
        """
        Execute an action
        This is done by sending the action to the game api which will then send it to the game server
        This method is used for all major actions
        It converts the game object to json and sends this json to the api

        :param action: The major action to be executed

        :return: The response from the game server in json format
        """
        if logger.isEnabledFor(logging.DEBUG):
            if isinstance(action, GameStateAction):
                logger.debug(f"Executing game state action with smaller actions {[type(at).__name__ for at in action.actions]}")
            else:
                logger.debug(f"Executing action {type(action).__name__}")

        json_action = dump_any(action)
        return self.game_api.make_game_server_request(json_action)

    def create_game_state_action(self, use_queue: bool=True, custom_actions: list[tuple[int, Action]]=None) -> GameState:
        """
        Create a game state action and execute it
        This is used to send multiple minor actions in one request
        It is used to update the game state

        It first takes all minor actions from the que and adds them to the game state action
        Then it uses the execute_action method to send the game state action to the api

        The response is then parsed to a game state object and returned

        :param use_queue: If true the actions from the que are used, if false custom_actions must be provided
        :param custom_actions: A linked list of custom actions to be used if use_queue is false

        :return: The response game state object
        """
        if custom_actions is not None and not isinstance(custom_actions, list):
            raise ValueError(f"custom_actions must be a list, not {type(custom_actions)}")

        if use_queue:
            actions_list = self.queue
            self.queue = []
        else:
            if custom_actions is None:
                actions_list = []
            else:
                actions_list = custom_actions
        self.past_actions = actions_list

        actions = LinkedList()
        for (action_uid, action) in actions_list:
            action.action_request_id = "actionReq-" + str(self.action_request_id)
            action.language = self.language
            actions.append(action)
            self.action_request_id_to_action_uid[action.action_request_id] =  action_uid
            self.action_request_id += 1

        if self.game_state is not None:
            state_ids, time_stamps = self.game_state.get_state_ids_and_time_stamps()
        else:
            state_ids, time_stamps = None, None

        game_state_action = GameStateAction(
            state_type=0,
            state_id="0",
            add_state_ids_on_sent=True,  # Only add state ids if we have a game state
            option=None,
            state_ids=state_ids,
            time_stamps=time_stamps,
            actions=actions
        )
        response_json = self.execute_action(game_state_action)
        if response_json["result"]["@c"] not in (GameState.C, "ultshared.UltAutoGameState"):
            raise ValueError(f"Action {response_json['result']} is not a GameState")
        game_state = parse_game_object(GameState, response_json["result"], self.game)
        if self.game_state:
            self.game_state.update(game_state)
        else:
            self.game_state = game_state

        # Set the action results
        for action_request_id, action_result in self.game_state.action_results.items():
            action_uid = self.action_request_id_to_action_uid[action_request_id]
            action_uid = int(action_uid)
            self.action_results[action_uid] = action_result

        if logger.isEnabledFor(logging.DEBUG):
            action_result_names = [f"{type(action).__name__}: {self.get_action_results().get(action_uid)}"
                                   for action_uid, action in self.past_actions]
            logger.debug(f"Action results of last GameState: {','.join(action_result_names) if len(action_result_names) > 0 else 'None'}")
        return self.game_state

    def activate_game(self, os, device, selected_player_id=0, selected_team_id=0,
                      random_team_country_selection=False) -> int:
        """
        Activate the game
        This is only called on join
        It creates a game activation action uses the execute_action method to send it to the api

        :param os: The operating system of the device.
        :param device: The device type
        :param selected_player_id: The selected player id
        :param selected_team_id: The selected team id
        :param random_team_country_selection: If the team selection is random

        :return: The player id
        """

        game_activation_action = GameActivationAction(selected_player_id, selected_team_id,
                                                      random_team_country_selection, os, device)

        response_json = self.execute_action(game_activation_action)
        try:
            raise GameActivationException.from_error_code(response_json["result"])
        except ValueError:
            pass
        self.game_api.player_id = response_json["result"]
        return response_json["result"]

    def get_action_results(self) -> dict[int, int]:
        return self.action_results