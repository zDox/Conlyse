import os
import pickle
from datetime import datetime
from typing import Literal
from typing import Union

from conflict_interface.data_types.game_state.game_state import GameState
from conflict_interface.data_types.static_map_data import StaticMapData
from conflict_interface.replay.replay_patch import AddOperation
from conflict_interface.replay.replay_patch import BidirectionalReplayPatch
from conflict_interface.replay.replay_patch import RemoveOperation
from conflict_interface.replay.replay_patch import ReplaceOperation
from conflict_interface.replayv2.metadata import Metadata
from conflict_interface.replayv2.patch_graph_node import PatchGraphNode
from conflict_interface.replayv2.replay_file import ReplayData


class Replay:
    def __init__(self, file_path: str, mode: Literal['r', 'w', 'a'] = 'r', game_id: int = None, player_id: int = None):
        self.file_path = file_path
        self.mode = mode
        self.game_id = game_id
        self.player_id = player_id

        self.data = ReplayData()

    def __enter__(self):
        return self.open()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def open(self):
        if self.mode == 'r':
            if not os.path.exists(self.file_path):
                raise FileNotFoundError(f"Replay file {self.file_path} does not exist.")

            self.data.load_full_from_disk(self.file_path)

        elif self.mode == 'a':
            if not os.path.exists(self.file_path):
                raise FileNotFoundError(f"Replay file {self.file_path} does not exist.")

            self.data.load_full_from_disk(self.file_path)

        elif self.mode == 'w':
            if self.game_id is None or self.player_id is None:
                raise ValueError("Game ID and Player ID must be provided in write mode")

            self.data.create_new_file(self.file_path)
            self.create_metadata()

        return self

    def close(self):
        if self.mode in ['w', 'a']:
            self.data.safe_to_disk(self.file_path)

    def create_metadata(self):
        info = {
            'game_id': self.game_id,
            'player_id': self.player_id,
            'start_time': 0,
            'last_time': 0,
            'end_time': None,
        }
        self.data.metadata = Metadata(info)

    def load_metadata(self) -> Metadata:
        pass # TODO

    def record_initial_game_state(self, game_state: GameState, time_stamp: datetime, game_id: int, player_id: int):
        self.validate_game(game_id, player_id)

        self.data.metadata.info['start_time'] = int(time_stamp.timestamp())
        self.data.metadata.info['last_time'] = int(time_stamp.timestamp())

        # copy the game state to avoid mutations
        self.data.initial_game_state = pickle.dumps(game_state)

    def record_static_map_data(self, static_map_data: StaticMapData,game_id: int, player_id: int):
        self.validate_game(game_id, player_id)

        self.data.static_map_data = pickle.dumps(static_map_data)

    def load_initial_game_state(self) -> GameState:
        if self.data.initial_game_state is None:
            raise ValueError("Initial game state is not recorded in the replay.")
        return pickle.loads(self.data.initial_game_state)

    def load_static_map_data(self) -> StaticMapData:
        if self.data.static_map_data is None:
            raise ValueError("Static map data is not recorded in the replay.")
        return pickle.loads(self.data.static_map_data)

    def record_bipatch(
            self,
            time_stamp: datetime,
            game_id: int,
            player_id: int,
            replay_patch: BidirectionalReplayPatch
    ):
        self.validate_game(game_id, player_id)

        from_timestamp = self.data.metadata.info['last_time']
        to_timestamp = int(time_stamp.timestamp())

        forward_operations = replay_patch.forward_patch.operations
        backward_operations = replay_patch.backward_patch.operations

        forward_node = PatchGraphNode(
            from_timestamp,
            to_timestamp,
            **self.ops_to_lists(forward_operations)
        )
        backward_node = PatchGraphNode(
            to_timestamp,
            from_timestamp,
            **self.ops_to_lists(backward_operations)
        )

        self.data.patches.append(forward_node)
        self.data.patches.append(backward_node)

        self.data.metadata.info['last_time'] = int(time_stamp.timestamp())

    def get_patch(self):
        pass # TODO

    def ops_to_lists(self, operations: list[Union[AddOperation, ReplaceOperation, RemoveOperation]]) -> dict[str, list]:
        op_types = []
        paths = []
        values = []


        for op in operations:
            paths.append(self.data.path_tree.get_or_add_path_node(op.path))

            if op.Key == 'a':
                op_types.append(1)
                values.append(op.new_value)
            elif op.Key == 'p':
                op_types.append(2)
                values.append(op.new_value)
            elif op.Key == 'r':
                op_types.append(3)
                values.append(None)
            else:
                raise ValueError(f"Unknown operation type: {type(op)}")

        return {
            'op_types': op_types,
            'paths': paths,
            'values': values
        }

    def validate_game(self, game_id: int, player_id: int):
        if self.game_id != game_id or self.player_id != player_id:
            raise ValueError("Game ID or Player ID does not match the initialized values.")




