from __future__ import annotations

import os
from copy import deepcopy
from datetime import UTC
from datetime import datetime
from logging import getLogger
from pathlib import Path
from typing import Any
from typing import Iterator

from typing import Literal
from typing import TYPE_CHECKING
from typing import Union

from conflict_interface.data_types.game_object import GameObject
from conflict_interface.data_types.game_object_binary import GameObjectSerializer
from conflict_interface.data_types.game_state.game_state import GameState
from conflict_interface.data_types.static_map_data import StaticMapData

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
from conflict_interface.utils.helper import create_parent_dirs

if TYPE_CHECKING:
    from conflict_interface.interface.game_interface import GameInterface
    from conflict_interface.interface.replay_interface import ReplayInterface

logger = getLogger()


class Replay:
    def __init__(self, file_path: Path, mode: Literal['r', 'w', 'a', 'rw'] = 'r', game_id: int = None, player_id: int = None, max_patches: int = None):
        self.file_path: Path = file_path
        self.mode = mode
        self.game_id = game_id
        self.player_id = player_id

        self._is_open = False

        self.storage = ReplayStorage()

        self._op_counter = 0
        self._game: ReplayInterface | None = None
        self._max_patches = max_patches

    def set_game(self, game: ReplayInterface):
        self._game = game

    def set_last_game_state(self, game_state: GameState):
        self.storage.last_game_state = game_state

    def set_max_patches(self, max_patches: int):
        self._max_patches = max_patches

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

            self.load_everything_into_memory()

        elif self.mode == 'a':
            if not os.path.exists(self.file_path):
                raise FileNotFoundError(f"Replay file {self.file_path} does not exist.")

            self.storage.read_append_mode_from_disk(self.file_path)
            self.storage.load_metadata()
            self.storage.load_last_game_state()
            self.storage.load_path_tree()

        elif self.mode == 'w':
            if self.game_id is None or self.player_id is None:
                raise ValueError("Game ID and Player ID must be provided in write mode")

            if self._max_patches is None:
                raise ValueError("Max Patches not set")

            create_parent_dirs(self.file_path)
            self.storage.initialize(self._max_patches)

        elif self.mode == 'rw':
            if self.game_id is None or self.player_id is None:
                raise ValueError("Game ID and Player ID must be provided in read write mode")

            if self._max_patches is None:
                raise ValueError("Max Patches not set")

            self.load_everything_into_memory()

        self._is_open = True
        return self

    def load_everything_into_memory(self):
        self.storage.read_full_from_disk(self.file_path)
        self.storage.load_metadata()
        self.storage.load_initial_game_state(self._game)
        self.storage.load_static_map_data(self._game)
        self.storage.load_path_tree()
        self.storage.load_patches(self._game)
        self.storage.path_tree.precompute()
        self.storage.patch_graph.finalize()

    def close(self):
        self.validate_max_patches()

        if self.mode in ['w', 'rw']:
            # When closing in write or read-write mode the replay gets defragmented. This improves read performance (maybe)
            self.storage.metadata.is_fragmented = False

            # Serialize everything
            self.storage.unload_metadata()
            self.storage.unload_path_tree()
            self.storage.unload_patches()
            self.storage.unload_last_game_state()

            # Assumes that initial-game-state and static-map-data have been unloaded on initial record
            # Write everything to file
            self.storage.write_full_to_disk(self.file_path)
        elif self.mode in ['a']:
            self.storage.update_metadata(self.file_path)
            self.storage.unload_last_game_state()
            self.storage.write_last_game_state(self.file_path)
            # no additional writes needed

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

    def record_patch_in_rw_mode(
            self,
            time_stamp: datetime,
            game_id: int,
            player_id: int,
            replay_patch: BidirectionalReplayPatch,
            game: GameInterface
    ):
        self.validate_game(game_id, player_id)
        self.validate_max_patches(2)

        from_timestamp = self.storage.metadata.last_time
        to_timestamp = int(time_stamp.timestamp())

        forward_operations = replay_patch.forward_patch.operations
        backward_operations = reversed(replay_patch.backward_patch.operations)

        self.storage.path_tree.fill_with_paths(forward_operations)

        forward = self.ops_to_lists(forward_operations, game)
        backward = self.ops_to_lists(backward_operations, game)

        forward_node = PatchGraphNode(
            from_timestamp=from_timestamp,
            to_timestamp=to_timestamp,
            op_types=forward['op_types'],
            paths = forward['paths'],
            values = forward['values']
        )
        backward_node = PatchGraphNode(
            from_timestamp=to_timestamp,
            to_timestamp=from_timestamp,
            op_types=backward['op_types'],
            paths=backward['paths'],
            values=backward['values']
        )

        self.storage.patch_graph.add_patch_node(forward_node)
        self.storage.patch_graph.add_patch_node(backward_node)
        self.storage.metadata.current_patches += 2

        self.storage.metadata.last_time = int(time_stamp.timestamp())

    def append_patches(self, time_stamp: datetime, game_id: int, player_id: int, replay_patches: list[BidirectionalReplayPatch]):
        self.validate_game(game_id, player_id)
        self.validate_max_patches(len(replay_patches)*2)

        if not self._is_open:
            logger.warning("Can not append to an closed replay")
            return
        if not self.mode == 'a':
            logger.warning(f"Can only append in Append mode, current mode is {self.mode}")
            return

        self.storage.metadata.is_fragmented = True
        from_timestamp = self.storage.metadata.last_time
        to_timestamp = int(time_stamp.timestamp())

        nodes = []
        all_new_paths = []
        for patch in replay_patches:
            new_nodes = self.storage.path_tree.fill_with_paths(patch.forward_patch.operations)
            new_paths = []
            for node in new_nodes:
                new_paths.append((node.index, node.parent.index if node.parent else 0, node.path_element))

            forward = self.ops_to_lists(patch.forward_patch.operations, None)
            backward = self.ops_to_lists(reversed(patch.backward_patch.operations), None)

            forward_node = PatchGraphNode(
                from_timestamp=from_timestamp,
                to_timestamp=to_timestamp,
                op_types=forward['op_types'],
                paths=forward['paths'],
                values=forward['values']
            )
            backward_node = PatchGraphNode(
                from_timestamp=to_timestamp,
                to_timestamp=from_timestamp,
                op_types=backward['op_types'],
                paths=backward['paths'],
                values=backward['values']
            )

            nodes.append(forward_node)
            nodes.append(backward_node)

            all_new_paths.append(new_paths)
            all_new_paths.append([]) # Assume forward and backwards have the same paths


        self.storage.metadata.last_time = int(time_stamp.timestamp())

        self.storage.append_patches_to_disk(nodes, all_new_paths, self.file_path)

    def apply_patch(self, patch: PatchGraphNode, game_state: GameState, game_interface: ReplayInterface):
        idx_to_node = self.storage.path_tree.idx_to_node

        def apply_op(_op_type, _value, _target, _pos, _node):
            apply_operation(_op_type, _value, _target, _pos)
            self._op_counter += 1
            if _node and _op_type == REMOVE_OPERATION:
                self.storage.path_tree.reset_child_references(_node.index)

        # Find operations that have unknown references
        unknown_ops, unknown_paths = [], []
        it = zip(patch.op_types, patch.paths, patch.values)
        for op_type, path_idx, value in it:
            node = idx_to_node[path_idx]
            if not node.reference:
                unknown_ops.append((op_type, path_idx, value))
                unknown_paths.append(path_idx)

        """ Note this code has an issue: When in a list a object is removed the references of all trailing elements is not made invalid"""
        # TODO fix this or note that its not allowed to delete from anywhere but the end of a list


        # Resolve unknown references using Steiner tree + BFS
        steiner_tree_adj = self.storage.path_tree.build_steiner_tree(unknown_paths)
        self.storage.path_tree.bfs_set_references(
            steiner_tree_adj,
            game_state
        )

        # Initialize hook system and safe old values
        hook_system = game_interface.get_hook_system()
        hook_data = {}
        if hook_system:
            hook_data = self.storage.path_tree.get_old_values(patch.paths, hook_system.get_hooks())

        # Apply resolved operations
        it = zip(patch.op_types, patch.paths, patch.values)
        for op_type, path_idx, value in it:
            node = idx_to_node[path_idx]
            apply_op(op_type, value, node.reference, node.path_element, node)

        # Get new values and que the hooks
        if hook_system:
            for hook_path, references in hook_data.items():
                for reference, attributes in references.items():
                    for attribute, value in attributes.items():
                        value[1] = getattr(reference, attribute, None)
                    hook_system.que_hook_path(hook_path, reference, attributes)


    def get_start_time(self) -> datetime:
        start_timestamp = self.storage.metadata.start_time
        return datetime.fromtimestamp(start_timestamp, tz=UTC)

    def get_last_time(self) -> datetime:
        last_timestamp = self.storage.metadata.last_time
        return datetime.fromtimestamp(last_timestamp, tz=UTC)

    def ops_to_lists(self, operations: list[Union[AddOperation, ReplaceOperation, RemoveOperation]] | Iterator[Any], game: GameInterface | None) -> dict[str, list]:
        op_types = []
        paths = []
        values = []

        for op in operations:
            idx = self.storage.path_tree.path_list_to_idx(op.path)
            paths.append(idx)

            if game is not None:
                GameObject.set_game_recursive(op.new_value, None)

            value = deepcopy(op.new_value)

            if game is not None:
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
            'values': values,
        }

    def validate_game(self, game_id: int, player_id: int):
        if self.game_id != game_id or self.player_id != player_id:
            raise ValueError("Game ID or Player ID does not match the initialized values.")
        if not self._is_open:
            raise ValueError("Replay file is not open.")

    def validate_structure(self):
        self.storage.patch_graph.validate_cached_time_stamps()
        self.storage.path_tree.validate_idx_to_node_mapping()
        self.storage.path_tree.validate_tree_structure()

    def validate_max_patches(self, add = 0):
        if self.storage.metadata.current_patches + add >= self.storage.metadata.max_patches:
            raise IndexError(
                f"Cannot add {add} patches: would exceed maximum of {self.storage.metadata.max_patches} "
                f"(currently at {self.storage.metadata.current_patches})"
            )





