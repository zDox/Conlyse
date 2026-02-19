from __future__ import annotations

from collections import deque
from datetime import UTC
from datetime import datetime
from logging import getLogger
from typing import TYPE_CHECKING


from conflict_interface.replay.apply_replay_helper import apply_operation
from conflict_interface.replay.patch_graph_node import PatchGraphNode
from conflict_interface.replay.replay_patch import BidirectionalReplayPatch
from conflict_interface.replay.replay_storage import ReplayStorage

if TYPE_CHECKING:
    from conflict_interface.interface.replay_interface import ReplayInterface
    from conflict_interface.data_types.newest.game_state.game_state import GameState
    from conflict_interface.data_types.newest.static_map_data import StaticMapData

logger = getLogger()



class ReplaySegment:
    def __init__(self, data: bytearray, version:int, game_id: int = None, player_id: int = None, max_patches: int = None):
        self.game_id = game_id
        self.player_id = player_id

        self.storage = ReplayStorage(data, version)

        self._op_counter = 0
        self._game: ReplayInterface | None = None
        self._max_patches = max_patches
        self._append_que = deque([])

    def set_game(self, game: ReplayInterface):
        self._game = game

    def set_last_game_state(self, game_state: GameState):
        self.storage.last_game_state = game_state

    def set_max_patches(self, max_patches: int):
        self._max_patches = max_patches

    def get_op_counter(self) -> int:
        return self._op_counter

    def reset_op_counter(self):
        self._op_counter = 0

    def load_everything(self):
        self.storage.read_all()
        self.storage.load_metadata()
        self.storage.load_initial_game_state(self._game)
        self.storage.load_static_map_data(self._game)
        self.storage.load_path_tree()
        self.storage.load_patches(self._game)
        self.storage.path_tree.precompute()
        self.storage.patch_graph.finalize()

    def load_append_mode(self):
        self.storage.read_append_mode_from_disk()
        self.storage.load_metadata()
        self.storage.load_last_game_state()
        self.storage.load_path_tree()

    def collapse_append_mode(self):
        self.validate_max_patches()
        self.storage.update_metadata()
        self.storage.unload_last_game_state()
        self.storage.write_last_game_state()

    def collapse_all(self):
        self.validate_max_patches()
        self.storage.metadata.is_fragmented = False

        # Serialize everything
        self.storage.unload_metadata()
        self.storage.unload_path_tree()
        self.storage.unload_patches()
        self.storage.unload_last_game_state()

        # Assumes that initial-game-state and static-map-data have been unloaded on initial record
        # Write everything to file
        self.storage.write_all()

    def record_initial_game_state(self, game_state: GameState, time_stamp: datetime, game_id: int, player_id: int):
        self.validate_game(game_id, player_id)

        self.storage.metadata.start_time = int(time_stamp.timestamp())
        self.storage.metadata.last_time = int(time_stamp.timestamp())

        # copy the game state to avoid mutations
        self.storage.unload_initial_game_state(game_state)

    def record_static_map_data(self, static_map_data: StaticMapData,game_id: int, player_id: int):
        self.validate_game(game_id, player_id)

        self.storage.unload_static_map_data(static_map_data)

    def _create_nodes_from_bireplay_patch(self, replay_patch: BidirectionalReplayPatch, from_timestamp: int, to_timestamp: int) -> tuple[PatchGraphNode, PatchGraphNode]:
        forward = replay_patch.forward_patch
        backward = replay_patch.backward_patch

        forward_path_ids = [self.storage.path_tree.path_list_to_idx(p) for p in forward.paths]
        backward_path_ids = [self.storage.path_tree.path_list_to_idx(p) for p in backward.paths]

        forward_node = PatchGraphNode(
            from_timestamp=from_timestamp,
            to_timestamp=to_timestamp,
            op_types=list(forward.op_types),
            paths=forward_path_ids,
            values=list(forward.values)
        )
        backward_node = PatchGraphNode(
            from_timestamp=to_timestamp,
            to_timestamp=from_timestamp,
            op_types=list(backward.op_types),
            paths=backward_path_ids,
            values=list(backward.values)
        )
        return forward_node, backward_node

    def record_patch_in_rw_mode(
            self,
            time_stamp: datetime,
            game_id: int,
            player_id: int,
            replay_patch: BidirectionalReplayPatch):

        self.validate_game(game_id, player_id)
        self.validate_max_patches(2)

        from_timestamp = self.storage.metadata.last_time
        to_timestamp = int(time_stamp.timestamp())

        self.storage.path_tree.fill_with_paths(replay_patch.forward_patch.paths)

        forward_node, backward_node = self._create_nodes_from_bireplay_patch(replay_patch, from_timestamp, to_timestamp)

        self.storage.patch_graph.add_edge_and_vertices(forward_node)
        self.storage.patch_graph.add_edge_and_vertices(backward_node)
        self.storage.patch_graph.finalize()
        self.storage.metadata.current_patches += 2

        self.storage.metadata.last_time = int(time_stamp.timestamp())

    def que_append_patch(self, time_stamp: datetime, game_id: int, player_id: int, replay_patch: BidirectionalReplayPatch):
        self.validate_game(game_id, player_id)
        self.validate_max_patches(2)


        self.storage.metadata.is_fragmented = True
        from_timestamp = self.storage.metadata.last_time
        to_timestamp = int(time_stamp.timestamp())

        nodes = []
        all_new_paths = []
        new_nodes = self.storage.path_tree.fill_with_paths(replay_patch.forward_patch.paths)
        new_paths = []

        for node in new_nodes:
            new_paths.append((node.index, node.parent.index if node.parent else 0, node.path_element))

        forward_node, backward_node = self._create_nodes_from_bireplay_patch(replay_patch, from_timestamp, to_timestamp)

        nodes.append(forward_node)
        nodes.append(backward_node)

        all_new_paths.append(new_paths)
        all_new_paths.append([]) # Assume forward and backwards have the same paths


        self.storage.metadata.last_time = int(time_stamp.timestamp())

        self._append_que.append((nodes, all_new_paths))

    def execute_append_que(self):
        all_nodes = []
        all_new_paths = []
        while self._append_que:
            nodes, new_paths = self._append_que.popleft()
            all_nodes.extend(nodes)
            all_new_paths.extend(new_paths)

        self.storage.append_patches_to_disk(all_nodes, all_new_paths)

    def apply_patch(self, patch: PatchGraphNode, game_state: GameState, game_interface: ReplayInterface):
        idx_to_node = self.storage.path_tree.idx_to_node

        def apply_op(_op_type, _value, _target, _pos):
            apply_operation(_op_type, _value, _target, _pos)
            self._op_counter += 1


        # Find operations that have unknown references
        unknown_ops, unknown_paths = [], []
        it = zip(patch.op_types, patch.paths, patch.values)
        for op_type, path_idx, value in it:
            node = idx_to_node[path_idx]
            if not node.reference:
                unknown_ops.append((op_type, path_idx, value))
                unknown_paths.append(path_idx)

        """ Note this code has an issue: When in a list a object is removed the references of all trailing elements is not made invalid"""

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
            apply_op(op_type, value, node.reference, node.path_element)
            self.storage.path_tree.reset_child_references(node.index)

        # Get new values and que the hooks
        if hook_system:
            for hook_path, references in hook_data.items():
                for obj_path, attributes in references.items():
                    reference = self.storage.path_tree.idx_to_node[obj_path].reference
                    for attribute, value in attributes.items():
                        value[1] = getattr(reference, attribute, None)
                    hook_system.que_hook_path(hook_path, reference, attributes)


    def get_start_time(self) -> datetime:
        start_timestamp = self.storage.metadata.start_time
        return datetime.fromtimestamp(start_timestamp, tz=UTC)

    def get_last_time(self) -> datetime:
        last_timestamp = self.storage.metadata.last_time
        return datetime.fromtimestamp(last_timestamp, tz=UTC)

    def validate_game(self, game_id: int, player_id: int):
        if self.game_id != game_id or self.player_id != player_id:
            raise ValueError("Game ID or Player ID does not match the initialized values.")

    def validate_structure(self):
        self.storage.path_tree.validate_idx_to_node_mapping()
        self.storage.path_tree.validate_tree_structure()

    def validate_max_patches(self, add = 0):
        if self.storage.metadata.current_patches + add >= self.storage.metadata.max_patches:
            raise IndexError(
                f"Cannot add {add} patches: would exceed maximum of {self.storage.metadata.max_patches} "
                f"(currently at {self.storage.metadata.current_patches})"
            )





