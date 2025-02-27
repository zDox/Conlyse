from datetime import datetime
from typing import Any

from conflict_interface.data_types import dump_any, GameObject, dump_dataclass, HashMap, LinkedList
from conflict_interface.data_types.action import Action
from conflict_interface.data_types.game_api_types.game_activation_action import GameActivationAction
from conflict_interface.data_types.game_api_types.game_state_action import GameStateAction


class ActionHandler:
    def __init__(self, game_api):
        self.actions: LinkedList[GameObject] = LinkedList()
        self.action_request_id = 0
        self.game_api = game_api
        self.language = "en" # TODO: Make this dynamic
        self.game_state = None

    def que_action(self, action, execute_immediately=False):
        if not issubclass(action, Action):
            raise ValueError(f"Action {action} is not a GameObject")
        if isinstance(action, GameStateAction):
            raise ValueError(f"GameStateAction {action} should not be added to the que but executed directly")
        if isinstance(action, GameActivationAction):
            raise ValueError(f"GameActivationAction {action} should not be added to the que but executed directly")

        if execute_immediately:
            self.execute_game_state_action(use_que=False, custom_actions=LinkedList([action]))

        self.actions.append(action)



    def execute_action(self, action: GameObject):
        json_action = dump_any(action)
        response = self.game_api.make_game_server_requst(json_action)

        # TODO do something with the response




    def execute_game_state_action(self, use_que = True, custom_actions = None):
        if use_que:
            actions = self.actions
        else:
            if custom_actions is None:
                raise ValueError("No custom actions provided")
            actions = custom_actions
        for action in actions:
            action.action_request_id = "actionReq-"+ str(self.action_request_id)
            action.language = self.language
            self.action_request_id += 1

        if self.game_state is not None:
            state_ids, time_stamps = self.game_state.get_state_ids()
        else:
            state_ids, time_stamps = HashMap(), HashMap()

        game_state_action = GameStateAction(
            state_type=0,
            state_id="0",
            add_state_ids_on_sent=(self.game_state is not None), # Only add state ids if we have a game state
            option=None,
            state_ids=state_ids,
            time_stamps=time_stamps,
            actions=actions
        )

        self.execute_action(game_state_action)


    def activate_game(self, os, device, selected_player_id=0, selected_team_id=0,
                      random_team_country_selection=False):

        game_activation_action = GameActivationAction(selected_player_id, selected_team_id, random_team_country_selection, os, device)

        self.execute_action(game_activation_action)


    def set_game_state(self, game_state):
        self.game_state = game_state

