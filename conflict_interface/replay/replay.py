from __future__ import annotations

import os
from copy import deepcopy
from datetime import UTC
from datetime import datetime
from pathlib import Path

from typing import Literal
from typing import TYPE_CHECKING
from typing import Union

from conflict_interface.data_types.game_object import GameObject
from conflict_interface.data_types.game_state.game_state import GameState
from conflict_interface.data_types.static_map_data import StaticMapData
from conflict_interface.interface.game_interface import GameInterface

from conflict_interface.replay.replay_patch import AddOperation
from conflict_interface.replay.replay_patch import BidirectionalReplayPatch
from conflict_interface.replay.replay_patch import RemoveOperation
from conflict_interface.replay.replay_patch import ReplaceOperation
from conflict_interface.replay.apply_replay_helper import apply_operation
from conflict_interface.replay.constants import ADD_OPERATION
from conflict_interface.replay.constants import REMOVE_OPERATION
from conflict_interface.replay.constants import REPLACE_OPERATION
from conflict_interface.replay.patch_graph_node import PatchGraphNode
from conflict_interface.replay.replay_storage import ReplayStorage

if TYPE_CHECKING:
    from conflict_interface.interface.replay_interface import ReplayInterface


class Replay:
    def __init__(self, file_path: Path, mode: Literal['r', 'w', 'a'] = 'r', game_id: int = None, player_id: int = None):
        self.file_path: Path = file_path
        self.mode = mode
        self.game_id = game_id
        self.player_id = player_id

        self._is_open = False

        self.storage = ReplayStorage()

        self._op_counter = 0
        self._game = None

    def set_game(self, game: ReplayInterface):
        self._game = game

    def __enter__(self):
        return self.open()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def get_op_counter(self) -> int:
        return self._op_counter

    def reset_op_counter(self):
        self._op_counter = 0

    def open(self):
        if self.mode == 'r':
            if not os.path.exists(self.file_path):
                raise FileNotFoundError(f"Replay file {self.file_path} does not exist.")

            self.storage.read_full_from_disk(self.file_path)
            self.storage.load_metadata()
            self.storage.load_initial_game_state(self._game)
            self.storage.load_static_map_data(self._game)
            self.storage.load_path_tree()
            self.storage.load_patches(self._game)
            self.storage.path_tree.precompute()
            # -----------
            # Safety Precautions
            self.storage.patch_graph.validate_cached_time_stamps()
            self.storage.path_tree.validate_idx_to_node_mapping()
            self.storage.path_tree.validate_tree_structure()
            # -----------

        elif self.mode == 'a':
            if not os.path.exists(self.file_path):
                raise FileNotFoundError(f"Replay file {self.file_path} does not exist.")

            self.storage.read_full_from_disk(self.file_path)
            self.storage.load_metadata()
            self.storage.load_initial_game_state(self._game)
            self.storage.load_static_map_data(self._game)
            self.storage.load_path_tree()
            self.storage.load_patches(self._game)
            self.storage.path_tree.precompute()
            # -----------
            # Safety Precautions
            self.storage.patch_graph.validate_cached_time_stamps()
            self.storage.path_tree.validate_idx_to_node_mapping()
            self.storage.path_tree.validate_tree_structure()
            # -----------

        elif self.mode == 'w':
            if self.game_id is None or self.player_id is None:
                raise ValueError("Game ID and Player ID must be provided in write mode")

            self.storage.create_new_file(self.file_path)
            self.storage.initialize()

        self._is_open = True
        return self

    def close(self):
        self.storage.unload_metadata()
        self.storage.unload_path_tree()
        self.storage.unload_patches()
        # Assumes that initial-game-state and static-map-data have been unloaded on initial record

        if self.mode in ['w', 'a']:
            self.storage.write_full_to_disk(self.file_path)

        self._is_open = False

    def record_initial_game_state(self, game_state: GameState, time_stamp: datetime, game_id: int, player_id: int):
        self.validate_game(game_id, player_id)

        self.storage.metadata.start_time = int(time_stamp.timestamp())
        self.storage.metadata.last_time = int(time_stamp.timestamp())

        # copy the game state to avoid mutations
        self.storage.unload_initial_game_state(game_state)

    def record_static_map_data(self, static_map_data: StaticMapData,game_id: int, player_id: int):
        self.validate_game(game_id, player_id)

        self.storage.unload_static_map_data(static_map_data)

    def record_patch(
            self,
            time_stamp: datetime,
            game_id: int,
            player_id: int,
            replay_patch: BidirectionalReplayPatch,
            game: GameInterface
    ):
        self.validate_game(game_id, player_id)

        from_timestamp = self.storage.metadata.last_time
        to_timestamp = int(time_stamp.timestamp())

        forward_operations = replay_patch.forward_patch.operations
        backward_operations = reversed(replay_patch.backward_patch.operations)

        forward_node = PatchGraphNode(
            from_timestamp,
            to_timestamp,
            **self.ops_to_lists(forward_operations, game)
        )
        backward_node = PatchGraphNode(
            to_timestamp,
            from_timestamp,
            **self.ops_to_lists(backward_operations, game)
        )

        self.storage.patch_graph.add_patch_node(forward_node)
        self.storage.patch_graph.add_patch_node(backward_node)

        self.storage.metadata.last_time = int(time_stamp.timestamp())

    def apply_patch(self, patch: PatchGraphNode, game_state: GameState, game_interface: ReplayInterface):
        idx_to_node = self.storage.path_tree.idx_to_node

        def apply_op(_op_type, _value, _target, _pos, _node=None):
            apply_operation(_op_type, _value, _target, _pos)
            self._op_counter += 1
            if _node and _op_type == REMOVE_OPERATION:
                _node.reference = None

        # Find operations that have unknown references
        unknown_ops, unknown_paths = [], []
        it = zip(patch.op_types, patch.paths, patch.values)
        for op_type, path_idx, value in it:
            node = idx_to_node[path_idx]
            if not node.reference:
                unknown_ops.append((op_type, path_idx, value))
                unknown_paths.append(path_idx)

        # Resolve unknown references using Steiner tree + BFS
        steiner_tree_adj = self.storage.path_tree.build_steiner_tree(unknown_paths)
        self.storage.path_tree.bfs_set_references(
            steiner_tree_adj,
            game_state
        )

        # Initialize hook system and safe old values
        hook_system = game_interface.get_hook_system()
        data_with_old = {}
        if hook_system:
            data_with_old = hook_system.get_old_values(patch.paths, self.storage.path_tree)

        # Apply resolved operations
        it = zip(patch.op_types, patch.paths, patch.values)
        for op_type, path_idx, value in it:
            node = idx_to_node[path_idx]
            apply_op(op_type, value, node.reference, node.path_element, node)

        # Get new values and que the hooks
        if hook_system:
            data_with_new = hook_system.set_new_values(data_with_old, self.storage.path_tree)
            for hook_path, reference_to_child, data in data_with_new:
                hook_system.que(hook_path, reference_to_child, data)

    def get_start_time(self) -> datetime:
        start_timestamp = self.storage.metadata.start_time
        return datetime.fromtimestamp(start_timestamp, tz=UTC)

    def get_last_time(self) -> datetime:
        last_timestamp = self.storage.metadata.last_time
        return datetime.fromtimestamp(last_timestamp, tz=UTC)

    def ops_to_lists(self, operations: list[Union[AddOperation, ReplaceOperation, RemoveOperation]], game: GameInterface) -> dict[str, list]:
        op_types = []
        paths = []
        values = []

        for op in operations:
            paths.append(self.storage.path_tree.get_or_add_path_node(op.path))

            GameObject.set_game_recursive(op.new_value, None)
            value = deepcopy(op.new_value)
            GameObject.set_game_recursive(op.new_value, game)

            if op.Key == 'a':
                op_types.append(ADD_OPERATION)
                values.append(value)
            elif op.Key == 'p':
                op_types.append(REPLACE_OPERATION)
                values.append(value)
            elif op.Key == 'r':
                op_types.append(REMOVE_OPERATION)
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
        if not self._is_open:
            raise ValueError("Replay file is not open.")




