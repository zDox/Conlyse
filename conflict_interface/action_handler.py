from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, cast, TYPE_CHECKING

from conflict_interface.data_types import dump_any, GameObject, dump_dataclass, HashMap, LinkedList, GameState, \
    parse_any, parse_game_object
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
    def __init__(self, game: GameInterface):
        self.actions: LinkedList[GameObject] = LinkedList()
        self.action_request_id = 0
        self.game_api: GameApi = game.get_api()
        self.game = game
        self.language = "en"  # TODO: Make this dynamic
        self.game_state = None

    def que_action(self, action: Action, execute_immediately=False):
        if not issubclass(action.__class__, Action):
            raise ValueError(f"Action {action} is not a GameObject")
        if isinstance(action, GameStateAction):
            raise ValueError(f"GameStateAction {action} should not be added to the que but executed directly")
        if isinstance(action, GameActivationAction):
            raise ValueError(f"GameActivationAction {action} should not be added to the que but executed directly")

        if execute_immediately:
            return self.execute_game_state_action(use_queue=False, custom_actions=LinkedList([action]))

        self.actions.append(action)

    def execute_action(self, action):
        if logger.isEnabledFor(logging.DEBUG):
            if isinstance(action, GameStateAction):
                logger.debug(f"Executing game state action with smaller actions {[type(at).__name__ for at in action.actions]}")
            else:
                logger.debug(f"Executing action {type(action).__name__}")

        json_action = dump_any(action)
        return self.game_api.make_game_server_request(json_action)

    def execute_game_state_action(self, use_queue=True, custom_actions=None) -> GameState:
        if use_queue:
            actions = self.actions
        else:
            if custom_actions is None:
                raise ValueError("No custom actions provided")
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
        self.game_state = game_state
