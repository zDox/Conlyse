from __future__ import annotations

import logging
from pprint import pprint
from typing import TYPE_CHECKING

from conflict_interface.data_types import dump_any, HashMap, LinkedList, GameState, \
    parse_game_object
from conflict_interface.data_types.action import Action
from conflict_interface.data_types.game_api_types.game_activation_action import GameActivationAction
from conflict_interface.data_types.game_api_types.game_state_action import GameStateAction
from conflict_interface.game_api import GameApi
from conflict_interface.logger_config import get_logger
from conflict_interface.utils.exceptions import GameActivationException

if TYPE_CHECKING:
    from conflict_interface.game_interface import GameInterface

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

    :ivar actions: A linked list of minor actions to be executed (the que)
    :ivar action_request_id: The current action request id it is incremented for each action needed for the req
    :ivar game_api: Reference to the game api
    :ivar game: Reference to the game interface
    :ivar language: The language of the game / the requests
    :ivar game_state: Reference to the current game state if available
    """
    def __init__(self, game: GameInterface):
        self.actions: LinkedList[Action] = LinkedList()
        self.action_request_id = 0
        self.game_api: GameApi = game.get_api()
        self.game = game
        self.language = "en"  # TODO: Make this dynamic
        self.game_state = None

    def que_action(self, action: Action):
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

        self.actions.append(action)

    def immediate_action(self, action: Action):
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

        return self.create_game_state_action(use_queue=False, custom_actions=LinkedList([action]))

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

    def create_game_state_action(self, use_queue: bool=True, custom_actions: LinkedList=None) -> GameState:
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
        if custom_actions is not None and not isinstance(custom_actions, LinkedList):
            raise ValueError(f"custom_actions must be a LinkedList, not {type(custom_actions)}")

        if use_queue:
            actions = self.actions
        else:
            if custom_actions is None:
                actions = LinkedList()
            else:
                actions = custom_actions

        for action in actions:
            action.action_request_id = "actionReq-" + str(self.action_request_id)
            action.language = self.language
            self.action_request_id += 1

        if self.game_state is not None:
            state_ids, time_stamps = self.game_state.get_state_ids()
        else:
            state_ids, time_stamps = HashMap(), HashMap()

        game_state_action = GameStateAction(
            state_type=0,
            state_id="0",
            add_state_ids_on_sent=(self.game_state is not None),  # Only add state ids if we have a game state
            option=None,
            state_ids=state_ids,
            time_stamps=time_stamps,
            actions=actions
        )
        response_json = self.execute_action(game_state_action)
        return parse_game_object(GameState, response_json["result"], self.game)

    def activate_game(self, os, device, selected_player_id=0, selected_team_id=0,
                      random_team_country_selection=False) -> int:
        """
        Activate the game
        This is only called on join
        It creates a game activation action uses the execute_action method to send it to the api

        :param os: The operating system of the device
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

    def set_game_state(self, game_state):
        """
        Set the game state
        This is used to update the game state in the action handler
        This will be one once the game state is created after the first request

        :param game_state: The game state to be set
        """
        self.game_state = game_state
