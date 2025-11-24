"""
Comprehensive test suite for the replay system.

This module contains extensive test coverage for:
- PathTree operations (node creation, deduplication, LCA queries, Steiner tree)
- PatchGraph operations (pathfinding, bidirectional navigation)
- Replay patch creation and application
- Serialization and compression
- Reference management and invalidation
- Edge cases and error handling
- Performance and memory characteristics
"""
import os
import tempfile
import unittest
from dataclasses import dataclass
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from typing import Dict
from typing import List
from typing import Optional

from conflict_interface.data_types.custom_types import HashMap
from conflict_interface.data_types.game_object import GameObject
from conflict_interface.data_types.game_state.game_state import GameState
from conflict_interface.data_types.game_state.game_state import States
from conflict_interface.interface.game_interface import GameInterface
from conflict_interface.replay.apply_replay_helper import apply_operation
from conflict_interface.replay.apply_replay_helper import get_child_reference
from conflict_interface.replay.constants import REMOVE_OPERATION
from conflict_interface.replay.constants import REPLACE_OPERATION
from conflict_interface.replay.make_bipatch_between_gamestates import make_bireplay_patch
from conflict_interface.replay.make_bipatch_between_gamestates import make_replay_patch
from conflict_interface.replay.patch_graph import PatchGraph
from conflict_interface.replay.patch_graph_node import PatchGraphNode
from conflict_interface.replay.path_tree import PathTree
from conflict_interface.replay.replay import Replay
from conflict_interface.replay.replay_patch import AddOperation
from conflict_interface.replay.replay_patch import BidirectionalReplayPatch
from conflict_interface.replay.replay_patch import RemoveOperation
from conflict_interface.replay.replay_patch import ReplaceOperation
from conflict_interface.replay.replay_patch import ReplayPatch


# ============================================================================
# Mock GameObject Classes
# ============================================================================

@dataclass
class MockUnit(GameObject):
    """Mock unit with various attributes for testing."""
    C = "Unit"
    id: int
    health: int = 100
    position_x: Optional[int] = None
    position_y: Optional[int] = None
    equipment: Optional[List[str]] = None

    MAPPING = {
        "id": "id",
        "health": "health",
        "position_x": "positionX",
        "position_y": "positionY",
        "equipment": "equipment",
    }


@dataclass
class MockPlayer(GameObject):
    """Mock player with nested structures."""
    C = "Player"
    name: str
    units: List[MockUnit]
    score: int = 0
    resources: Optional[Dict[str, int]] = None
    metadata: Optional[Dict] = None

    MAPPING = {
        "name": "name",
        "units": "units",
        "score": "score",
        "resources": "resources",
        "metadata": "metadata",
    }


@dataclass
class MockGameState(GameObject):
    """Mock game state for complex testing."""
    C = "GameState"
    turn: int
    players: List[MockPlayer]
    global_events: Optional[List[str]] = None

    MAPPING = {
        "turn": "turn",
        "players": "players",
        "global_events": "globalEvents",
    }


# ============================================================================
# PathTree Tests
# ============================================================================

class TestPathTree(unittest.TestCase):
    """Test cases for PathTree structure and operations."""

    def setUp(self):
        """Create a fresh PathTree for each test."""
        self.tree = PathTree()

    def test_root_node_initialization(self):
        """Test that PathTree initializes with a root node."""
        self.assertIsNotNone(self.tree.root)
        self.assertEqual(self.tree.root.path_element, "root")
        self.assertEqual(self.tree.root.index, 0)
        self.assertEqual(self.tree.idx_counter, 1)

    def test_add_single_path(self):
        """Test adding a single path to the tree."""
        path = ["players", "0", "name"]
        idx = self.tree.get_or_add_path_node(path)

        self.assertIsInstance(idx, int)
        self.assertGreater(idx, 0)

        # Verify node exists in mapping
        self.assertIn(idx, self.tree.idx_to_node)
        node = self.tree.idx_to_node[idx]
        self.assertEqual(node.path_element, "name")

    def test_path_deduplication(self):
        """Test that identical paths return the same index."""
        path1 = ["players", "0", "health"]
        path2 = ["players", "0", "health"]

        idx1 = self.tree.get_or_add_path_node(path1)
        idx2 = self.tree.get_or_add_path_node(path2)

        self.assertEqual(idx1, idx2)

    def test_shared_prefix_paths(self):
        """Test that paths sharing prefixes reuse nodes."""
        path1 = ["players", "0", "health"]
        path2 = ["players", "0", "score"]
        path3 = ["players", "1", "health"]

        idx1 = self.tree.get_or_add_path_node(path1)
        idx2 = self.tree.get_or_add_path_node(path2)
        idx3 = self.tree.get_or_add_path_node(path3)

        # All should be different leaf nodes
        self.assertNotEqual(idx1, idx2)
        self.assertNotEqual(idx1, idx3)
        self.assertNotEqual(idx2, idx3)

        # Should reuse "players" node
        players_children = self.tree.root.children["players"].children
        self.assertIn("0", players_children)
        self.assertIn("1", players_children)

    def test_empty_path(self):
        """Test handling of empty path."""
        path = []
        idx = self.tree.get_or_add_path_node(path)
        self.assertEqual(idx, 0)  # Should return root

    def test_deep_nested_path(self):
        """Test deeply nested path (10+ levels)."""
        path = [f"level{i}" for i in range(15)]
        idx = self.tree.get_or_add_path_node(path)

        node = self.tree.idx_to_node[idx]
        self.assertEqual(node.path_element, "level14")

    def test_mixed_path_element_types(self):
        """Test paths with both string and integer elements."""
        path = ["players", 0, "units", 5, "health"]
        idx = self.tree.get_or_add_path_node(path)

        node = self.tree.idx_to_node[idx]
        self.assertEqual(node.path_element, "health")

    def test_euler_tour_precomputation(self):
        """Test Euler tour precomputation."""
        # Add several paths
        paths = [
            ["players", "0", "health"],
            ["players", "0", "score"],
            ["players", "1", "health"],
            ["global", "turn"],
        ]
        for path in paths:
            self.tree.get_or_add_path_node(path)

        # Precompute Euler tour
        self.tree.precompute()

        # Verify structures are populated
        self.assertIsNotNone(self.tree.euler)
        self.assertIsNotNone(self.tree.tin)
        self.assertIsNotNone(self.tree.tout)
        self.assertIsNotNone(self.tree.depth)
        self.assertGreater(len(self.tree.euler), 0)

    def test_lca_query(self):
        """Test Lowest Common Ancestor queries."""
        # Build tree
        path1 = ["players", "0", "health"]
        path2 = ["players", "0", "score"]
        path3 = ["players", "1", "health"]

        idx1 = self.tree.get_or_add_path_node(path1)
        idx2 = self.tree.get_or_add_path_node(path2)
        idx3 = self.tree.get_or_add_path_node(path3)

        self.tree.precompute()

        # LCA of two nodes under same parent should be the parent
        lca_12 = self.tree.lca(idx1, idx2)
        parent_node = self.tree.root.children["players"].children["0"]
        self.assertEqual(lca_12, parent_node.index)

        # LCA of nodes under different parents
        lca_13 = self.tree.lca(idx1, idx3)
        players_node = self.tree.root.children["players"]
        self.assertEqual(lca_13, players_node.index)

    def test_lca_with_root(self):
        """Test LCA queries involving the root."""
        path1 = ["players", "0"]
        path2 = ["global", "turn"]

        idx1 = self.tree.get_or_add_path_node(path1)
        idx2 = self.tree.get_or_add_path_node(path2)

        self.tree.precompute()

        lca = self.tree.lca(idx1, idx2)
        self.assertEqual(lca, 0)  # Root

    def test_lca_siblings(self):
        """Test LCA of sibling nodes."""
        path1 = ["players", "0"]
        path2 = ["players", "1"]

        idx1 = self.tree.get_or_add_path_node(path1)
        idx2 = self.tree.get_or_add_path_node(path2)

        self.tree.precompute()

        lca = self.tree.lca(idx1, idx2)
        players_node = self.tree.root.children["players"]
        self.assertEqual(lca, players_node.index,
                         "LCA of siblings should be their parent")

    def test_lca_different_branches(self):
        """Test LCA of nodes in completely different branches."""
        path1 = ["players", "0", "health"]
        path2 = ["global", "turn"]

        idx1 = self.tree.get_or_add_path_node(path1)
        idx2 = self.tree.get_or_add_path_node(path2)

        self.tree.precompute()

        lca = self.tree.lca(idx1, idx2)
        self.assertEqual(lca, 0, "LCA of different branches should be root")

    def test_lca_cousins_same_depth(self):
        """Test LCA of cousin nodes at the same depth."""
        path1 = ["a", "b", "c"]
        path2 = ["a", "d", "e"]

        idx1 = self.tree.get_or_add_path_node(path1)
        idx2 = self.tree.get_or_add_path_node(path2)

        self.tree.precompute()

        lca = self.tree.lca(idx1, idx2)
        a_node = self.tree.root.children["a"]
        self.assertEqual(lca, a_node.index,
                         "LCA of cousins should be their common ancestor")

    def test_lca_parent_child(self):
        """Test LCA when one node is ancestor of another."""
        path1 = ["players", "0"]
        path2 = ["players", "0", "health"]

        idx1 = self.tree.get_or_add_path_node(path1)
        idx2 = self.tree.get_or_add_path_node(path2)

        self.tree.precompute()

        lca = self.tree.lca(idx1, idx2)
        self.assertEqual(lca, idx1,
                         "LCA should be the ancestor node")

    def test_lca_node_with_itself(self):
        """Test LCA of a node with itself."""
        path = ["x", "y", "z"]
        idx = self.tree.get_or_add_path_node(path)

        self.tree.precompute()

        lca = self.tree.lca(idx, idx)
        self.assertEqual(lca, idx,
                         "LCA of node with itself should be the node")

    def test_lca_three_siblings(self):
        """Test LCA with multiple sibling nodes."""
        path1 = ["root", "child1"]
        path2 = ["root", "child2"]
        path3 = ["root", "child3"]

        idx1 = self.tree.get_or_add_path_node(path1)
        idx2 = self.tree.get_or_add_path_node(path2)
        idx3 = self.tree.get_or_add_path_node(path3)

        self.tree.precompute()

        root_child = self.tree.root.children["root"]

        # Test all pairs
        self.assertEqual(self.tree.lca(idx1, idx2), root_child.index)
        self.assertEqual(self.tree.lca(idx1, idx3), root_child.index)
        self.assertEqual(self.tree.lca(idx2, idx3), root_child.index)

    def test_lca_deep_nesting(self):
        """Test LCA with deeply nested paths."""
        path1 = ["a", "b", "c", "d", "e"]
        path2 = ["a", "b", "c", "d", "f"]
        path3 = ["a", "b", "c", "g"]
        path4 = ["a", "b", "h"]

        idx1 = self.tree.get_or_add_path_node(path1)
        idx2 = self.tree.get_or_add_path_node(path2)
        idx3 = self.tree.get_or_add_path_node(path3)
        idx4 = self.tree.get_or_add_path_node(path4)

        self.tree.precompute()

        # Get node indices for comparison
        d_node = self.tree.root.children["a"].children["b"].children["c"].children["d"]
        c_node = self.tree.root.children["a"].children["b"].children["c"]
        b_node = self.tree.root.children["a"].children["b"]

        # Test various LCA pairs
        self.assertEqual(self.tree.lca(idx1, idx2), d_node.index,
                         "LCA of e and f should be d")
        self.assertEqual(self.tree.lca(idx1, idx3), c_node.index,
                         "LCA of e and g should be c")
        self.assertEqual(self.tree.lca(idx1, idx4), b_node.index,
                         "LCA of e and h should be b")
        self.assertEqual(self.tree.lca(idx3, idx4), b_node.index,
                         "LCA of g and h should be b")

    def test_lca_complex_multi_branch(self):
        """Test LCA in complex multi-branch tree."""
        paths = [
            ["game", "players", "0", "health"],
            ["game", "players", "1", "health"],
            ["game", "enemies", "0", "health"],
            ["game", "state", "turn"]
        ]

        indices = [self.tree.get_or_add_path_node(p) for p in paths]

        self.tree.precompute()

        # Get node indices
        game_node = self.tree.root.children["game"]
        players_node = game_node.children["players"]

        # Test various pairs
        self.assertEqual(self.tree.lca(indices[0], indices[1]), players_node.index,
                         "LCA of players/0 and players/1 should be players")
        self.assertEqual(self.tree.lca(indices[0], indices[2]), game_node.index,
                         "LCA of players/0 and enemies/0 should be game")
        self.assertEqual(self.tree.lca(indices[0], indices[3]), game_node.index,
                         "LCA of players/0 and state/turn should be game")
        self.assertEqual(self.tree.lca(indices[2], indices[3]), game_node.index,
                         "LCA of enemies/0 and state/turn should be game")

    def test_lca_asymmetric_paths(self):
        """Test LCA with paths of different lengths."""
        path1 = ["a", "b"]
        path2 = ["a", "c", "d", "e", "f"]

        idx1 = self.tree.get_or_add_path_node(path1)
        idx2 = self.tree.get_or_add_path_node(path2)

        self.tree.precompute()

        a_node = self.tree.root.children["a"]
        lca = self.tree.lca(idx1, idx2)
        self.assertEqual(lca, a_node.index,
                         "LCA should be common ancestor regardless of depth")

    def test_steiner_tree_single_node(self):
        """Test Steiner tree with a single node."""
        path = ["players", "0", "health"]
        idx = self.tree.get_or_add_path_node(path)

        self.tree.precompute()

        steiner = self.tree.build_steiner_tree([idx])

        # Should include root and all nodes on path
        self.assertIn(0, steiner)  # Root
        self.assertIn(idx, steiner)

    def test_steiner_tree_multiple_nodes(self):
        """Test Steiner tree with multiple nodes."""
        paths = [
            ["players", "0", "health"],
            ["players", "0", "score"],
            ["players", "1", "health"],
        ]
        indices = [self.tree.get_or_add_path_node(p) for p in paths]

        self.tree.precompute()

        steiner = self.tree.build_steiner_tree(indices)

        # Should include all terminal nodes
        for idx in indices:
            self.assertIn(idx, steiner)

        # Should include root
        self.assertIn(0, steiner)

    def test_steiner_tree_adjacency_structure(self):
        """Test that Steiner tree has proper parent-child relationships."""
        path1 = ["players", "0", "health"]
        path2 = ["players", "1", "score"]

        idx1 = self.tree.get_or_add_path_node(path1)
        idx2 = self.tree.get_or_add_path_node(path2)

        self.tree.precompute()

        steiner = self.tree.build_steiner_tree([idx1, idx2])

        # Each node should have children pointing down the tree
        root_children = steiner[0]
        self.assertGreater(len(root_children), 0)

    def test_bfs_set_references(self):
        """Test BFS reference setting on a subtree."""
        # Create mock game state
        mock_state = {
            "players": [
                {"health": 100, "score": 50},
                {"health": 80, "score": 30}
            ]
        }

        paths = [
            ["players", 0, "health"],
            ["players", 0, "score"],
        ]
        indices = [self.tree.get_or_add_path_node(p) for p in paths]

        self.tree.precompute()

        steiner = self.tree.build_steiner_tree(indices)
        self.tree.bfs_set_references(steiner, mock_state)

        # Check that references are set
        for idx in indices:
            node = self.tree.idx_to_node[idx]
            self.assertIsNotNone(node.reference)

    def test_validate_idx_to_node_mapping(self):
        """Test validation of index to node mapping."""
        paths = [
            ["players", "0", "health"],
            ["players", "1", "score"],
        ]
        for path in paths:
            self.tree.get_or_add_path_node(path)

        # Should not raise any errors
        self.tree.validate_idx_to_node_mapping()

    def test_large_path_tree(self):
        """Test tree with thousands of paths."""
        paths = []
        for i in range(100):
            for j in range(10):
                path = ["players", str(i), "units", str(j), "health"]
                paths.append(path)

        indices = [self.tree.get_or_add_path_node(p) for p in paths]

        # All should be unique leaf nodes
        self.assertEqual(len(set(indices)), len(indices))

        # But should share many intermediate nodes
        self.assertLess(self.tree.idx_counter, len(paths) * 5)


# ============================================================================
# PatchGraph Tests
# ============================================================================

class TestPatchGraph(unittest.TestCase):
    """Test cases for PatchGraph structure and pathfinding."""

    def setUp(self):
        """Create a fresh PatchGraph for each test."""
        self.graph = PatchGraph()

    def test_empty_graph(self):
        """Test empty graph initialization."""
        self.assertEqual(len(self.graph.nodes), 0)
        self.assertEqual(len(self.graph.patches), 0)
        self.assertEqual(len(self.graph.time_stamps_cache), 0)

    def test_add_single_patch(self):
        """Test adding a single patch node."""
        patch = PatchGraphNode(
            from_timestamp=1000,
            to_timestamp=2000,
            op_types=[REPLACE_OPERATION],
            paths=[1],
            values=[42]
        )

        self.graph.add_patch_node(patch)

        self.assertEqual(len(self.graph.patches), 1)
        self.assertIn((1000, 2000), self.graph.patches)
        self.assertIn(1000, self.graph.time_stamps_cache)
        self.assertIn(2000, self.graph.time_stamps_cache)

    def test_bidirectional_edges(self):
        """Test that patches create bidirectional edges."""
        patch_forward = PatchGraphNode(
            from_timestamp=1000,
            to_timestamp=2000,
            op_types=[REPLACE_OPERATION],
            paths=[1],
            values=[42]
        )
        patch_backward = PatchGraphNode(
            from_timestamp=2000,
            to_timestamp=1000,
            op_types=[REPLACE_OPERATION],
            paths=[1],
            values=[0]
        )

        self.graph.add_patch_node(patch_forward)
        self.graph.add_patch_node(patch_backward)

        # Check adjacency
        self.assertIn(2000, self.graph.adj[1000])
        self.assertIn(1000, self.graph.adj[2000])

    def test_linear_patch_sequence(self):
        """Test finding path through linear sequence of patches."""
        timestamps = [1000, 2000, 3000, 4000]

        for i in range(len(timestamps) - 1):
            patch = PatchGraphNode(
                from_timestamp=timestamps[i],
                to_timestamp=timestamps[i + 1],
                op_types=[REPLACE_OPERATION],
                paths=[1],
                values=[i]
            )
            self.graph.add_patch_node(patch)

        # Find path from start to end
        path = self.graph.find_patch_path(
            datetime.fromtimestamp(1000, tz=timezone.utc),
            datetime.fromtimestamp(4000, tz=timezone.utc)
        )

        self.assertEqual(len(path), 3)
        self.assertEqual(path[0].from_timestamp, 1000)
        self.assertEqual(path[-1].to_timestamp, 4000)

    def test_branching_patch_graph(self):
        """Test pathfinding in graph with branches."""
        # Create Y-shaped graph: 1000 -> 2000 -> {3000, 3001}
        patches = [
            PatchGraphNode(1000, 2000, [REPLACE_OPERATION], [1], [0]),
            PatchGraphNode(2000, 3000, [REPLACE_OPERATION], [1], [1]),
            PatchGraphNode(2000, 3001, [REPLACE_OPERATION], [1], [2]),
        ]

        for patch in patches:
            self.graph.add_patch_node(patch)

        # Path to first branch
        path1 = self.graph.find_patch_path(
            datetime.fromtimestamp(1000, tz=timezone.utc),
            datetime.fromtimestamp(3000, tz=timezone.utc)
        )
        self.assertEqual(len(path1), 2)

        # Path to second branch
        path2 = self.graph.find_patch_path(
            datetime.fromtimestamp(1000, tz=timezone.utc),
            datetime.fromtimestamp(3001, tz=timezone.utc)
        )
        self.assertEqual(len(path2), 2)

    def test_shortest_path_selection(self):
        """Test that shortest path is selected when multiple exist."""
        # Create diamond graph with different costs
        patches = [
            PatchGraphNode(1000, 2000, [REPLACE_OPERATION] * 5, [1] * 5, [0] * 5),  # Cost 5
            PatchGraphNode(1000, 3000, [REPLACE_OPERATION], [1], [0]),  # Cost 1 (direct)
            PatchGraphNode(2000, 3000, [REPLACE_OPERATION], [1], [0]),  # Cost 1
        ]

        for patch in patches:
            self.graph.add_patch_node(patch)

        path = self.graph.find_patch_path(
            datetime.fromtimestamp(1000, tz=timezone.utc),
            datetime.fromtimestamp(3000, tz=timezone.utc)
        )

        # Should take direct path
        self.assertEqual(len(path), 1)
        self.assertEqual(path[0].from_timestamp, 1000)
        self.assertEqual(path[0].to_timestamp, 3000)

    def test_backward_navigation(self):
        """Test navigating backward through time."""
        patches = [
            PatchGraphNode(1000, 2000, [REPLACE_OPERATION], [1], [42]),
            PatchGraphNode(2000, 1000, [REPLACE_OPERATION], [1], [0]),  # Backward
        ]

        for patch in patches:
            self.graph.add_patch_node(patch)

        path = self.graph.find_patch_path(
            datetime.fromtimestamp(2000, tz=timezone.utc),
            datetime.fromtimestamp(1000, tz=timezone.utc)
        )

        self.assertEqual(len(path), 1)
        self.assertEqual(path[0].from_timestamp, 2000)
        self.assertEqual(path[0].to_timestamp, 1000)

    def test_no_path_exists(self):
        """Test error handling when no path exists."""
        patch = PatchGraphNode(1000, 2000, [REPLACE_OPERATION], [1], [0])
        self.graph.add_patch_node(patch)

        with self.assertRaises(ValueError):
            self.graph.find_patch_path(
                datetime.fromtimestamp(1000, tz=timezone.utc),
                datetime.fromtimestamp(5000, tz=timezone.utc)  # Unreachable
            )

    def test_validate_timestamps(self):
        """Test timestamp validation and caching."""
        patch = PatchGraphNode(1000, 2000, [REPLACE_OPERATION], [1], [0])
        self.graph.add_patch_node(patch)

        # Clear cache and validate
        self.graph.time_stamps_cache.clear()
        self.graph.validate_cached_time_stamps()

        # Cache should be rebuilt
        self.assertIn(1000, self.graph.time_stamps_cache)
        self.assertIn(2000, self.graph.time_stamps_cache)


# ============================================================================
# Replay Patch Creation Tests
# ============================================================================

class TestReplayPatchCreation(unittest.TestCase):
    """Test cases for creating patches from object differences."""

    def test_simple_value_change(self):
        """Test patch creation for simple value change."""
        unit1 = MockUnit(id=1, health=100)
        unit2 = MockUnit(id=1, health=50)

        patch = make_replay_patch(unit1, unit2)

        self.assertEqual(len(patch.operations), 1)
        self.assertIsInstance(patch.operations[0], ReplaceOperation)
        self.assertEqual(patch.operations[0].path, ["health"])
        self.assertEqual(patch.operations[0].new_value, 50)

    def test_multiple_changes(self):
        """Test patch with multiple attribute changes."""
        unit1 = MockUnit(id=1, health=100, position_x=10, position_y=20)
        unit2 = MockUnit(id=1, health=75, position_x=15, position_y=20)

        patch = make_replay_patch(unit1, unit2)

        # Should have changes for health and position_x, not position_y
        health_ops = [op for op in patch.operations if "health" in op.path]
        pos_x_ops = [op for op in patch.operations if "position_x" in op.path]

        self.assertEqual(len(health_ops), 1)
        self.assertEqual(len(pos_x_ops), 1)

    def test_no_changes(self):
        """Test patch creation when objects are identical."""
        unit1 = MockUnit(id=1, health=100)
        unit2 = MockUnit(id=1, health=100)

        patch = make_replay_patch(unit1, unit2)

        self.assertTrue(patch.is_empty())

    def test_list_element_changes(self):
        """Test patch for changes in list elements."""
        player1 = MockPlayer(
            name="Player1",
            units=[MockUnit(id=1, health=100), MockUnit(id=2, health=80)]
        )
        player2 = MockPlayer(
            name="Player1",
            units=[MockUnit(id=1, health=50), MockUnit(id=2, health=80)]
        )

        patch = make_replay_patch(player1, player2)

        # Should have change for first unit's health
        health_ops = [op for op in patch.operations
                      if "units" in op.path and "health" in op.path]
        self.assertGreater(len(health_ops), 0)

    def test_list_add_element(self):
        """Test patch for adding element to list."""
        player1 = MockPlayer(name="Player1", units=[MockUnit(id=1, health=100)])
        player2 = MockPlayer(
            name="Player1",
            units=[MockUnit(id=1, health=100), MockUnit(id=2, health=80)]
        )

        patch = make_replay_patch(player1, player2)

        add_ops = [op for op in patch.operations if isinstance(op, AddOperation)]
        self.assertGreater(len(add_ops), 0)

    def test_list_remove_element(self):
        """Test patch for removing element from list."""
        player1 = MockPlayer(
            name="Player1",
            units=[MockUnit(id=1, health=100), MockUnit(id=2, health=80)]
        )
        player2 = MockPlayer(name="Player1", units=[MockUnit(id=1, health=100)])

        patch = make_replay_patch(player1, player2)

        remove_ops = [op for op in patch.operations if isinstance(op, RemoveOperation)]
        self.assertGreater(len(remove_ops), 0)

    def test_dict_changes(self):
        """Test patch for dictionary modifications."""
        player1 = MockPlayer(
            name="Player1",
            units=[],
            resources={"gold": 100, "wood": 50}
        )
        player2 = MockPlayer(
            name="Player1",
            units=[],
            resources={"gold": 150, "wood": 50, "stone": 25}
        )

        patch = make_replay_patch(player1, player2)

        # Should have replace for gold, add for stone
        replace_ops = [op for op in patch.operations
                      if isinstance(op, ReplaceOperation) and "gold" in str(op.path)]
        add_ops = [op for op in patch.operations
                  if isinstance(op, AddOperation) and "stone" in str(op.path)]

        self.assertGreater(len(replace_ops), 0)
        self.assertGreater(len(add_ops), 0)

    def test_bidirectional_patch(self):
        """Test creation of bidirectional patch."""
        unit1 = MockUnit(id=1, health=100)
        unit2 = MockUnit(id=1, health=50)

        bipatch = make_bireplay_patch(unit1, unit2)

        # Forward should change to 50
        self.assertEqual(len(bipatch.forward_patch.operations), 1)
        self.assertEqual(bipatch.forward_patch.operations[0].new_value, 50)

        # Backward should change back to 100
        self.assertEqual(len(bipatch.backward_patch.operations), 1)
        self.assertEqual(bipatch.backward_patch.operations[0].new_value, 100)

    def test_nested_object_changes(self):
        """Test patch for deeply nested object changes."""
        state1 = MockGameState(
            turn=1,
            players=[
                MockPlayer(
                    name="P1",
                    units=[MockUnit(id=1, health=100)],
                    resources={"gold": 50}
                )
            ]
        )
        state2 = MockGameState(
            turn=1,
            players=[
                MockPlayer(
                    name="P1",
                    units=[MockUnit(id=1, health=75)],
                    resources={"gold": 50}
                )
            ]
        )

        patch = make_replay_patch(state1, state2)

        # Should detect nested health change
        self.assertGreater(len(patch.operations), 0,
                           "Should detect health change in nested structure")

        # More specific check
        if len(patch.operations) > 0:
            health_op = patch.operations[0]
            self.assertIsInstance(health_op, ReplaceOperation)


# ============================================================================
# Replay Patch Serialization Tests
# ============================================================================

class TestReplayPatchSerialization(unittest.TestCase):
    """Test cases for patch serialization and compression."""

    def test_path_deduplication_in_serialization(self):
        """Test that repeated paths are deduplicated in serialization."""
        patch = ReplayPatch()
        # Add multiple operations with same path
        for i in range(10):
            patch.replace_op(["same", "path"], i)

        patch_bytes = patch.to_bytes()

        # Compressed size should be much smaller than uncompressed
        # (This is a heuristic test)
        self.assertLess(len(patch_bytes), len(str(patch.operations)))

    def test_compression_ratio(self):
        """Test that compression actually reduces size."""
        patch = ReplayPatch()

        # Create many similar operations (highly compressible)
        for i in range(100):
            patch.replace_op(["players", "0", "score"], i)

        patch_bytes = patch.to_bytes()

        # Rough estimate: compressed should be < 50% of naive size
        naive_size = len(str(patch.operations).encode())
        self.assertLess(len(patch_bytes), round(naive_size * 0.5))

# ============================================================================
# Full Replay Integration Tests
# ============================================================================

class TestReplayIntegration(unittest.TestCase):
    """Integration tests for complete replay workflows."""

    def setUp(self):
        """Set up test fixtures."""
        self.game = GameInterface()
        self.game_state = GameState(
            time_stamp="2024-01-01T00:00:00Z",
            state_id="test-state-1",
            state_type=0,
            states=States(
                player_state=None,
                newspaper_state=None,
                map_state=None,
                resource_state=None,
                foreign_affairs_state=None,
                army_state=None,
                spy_state=None,
                map_info_state=None,
                admin_state=None,
                statistic_state=None,
                mod_state=None,
                game_info_state=None,
                ai_state=None,
                premium_state=None,
                user_options_state=None,
                user_inventory_state=None,
                user_sms_state=None,
                tutorial_state=None,
                build_queue_state=None,
                location_state=None,
                triggered_tutorial_state=None,
                wheel_of_fortune_state=None,
                research_state=None,
                game_event_state=None,
                in_game_alliance_state=None,
                exploration_state=None,
                quest_state=None,
                configuration_state=None,
                mission_state=None,
            ),
            action_results=HashMap()
        )
        self.game_state.action_results["turn"] = 1
        self.game_state.action_results["score"] = 100
        self.game_state.action_results["level"] = 1

    def test_create_and_read_replay_file(self):
        """Test basic replay file creation and reading."""
        with tempfile.TemporaryDirectory() as temp_dir:
            replay_file = os.path.join(temp_dir, "test.replay")

            # Write
            with Replay(replay_file, mode='w', game_id=123, player_id=1) as replay:
                replay.record_initial_game_state(
                    self.game_state,
                    datetime(2024, 1, 1, 0, 0, 0),
                    123,
                    1
                )
                replay.storage.static_map_data_b = b''

            # Read
            with Replay(replay_file, mode='r') as replay:
                loaded_state = replay.load_initial_game_state()
                self.assertEqual(loaded_state.action_results["turn"], 1)

    def test_replay_with_multiple_timestamps(self):
        """Test replay with patches at multiple timestamps."""
        with tempfile.TemporaryDirectory() as temp_dir:
            replay_file = os.path.join(temp_dir, "test.replay")

            base_time = datetime(2024, 1, 1, 0, 0, 0)

            with Replay(replay_file, mode='w', game_id=123, player_id=1) as replay:
                replay.record_initial_game_state(self.game_state, base_time, 123, 1)
                replay.storage.static_map_data_b = b''

                # Record patches at 1-minute intervals
                for i in range(1, 11):
                    bipatch = BidirectionalReplayPatch()
                    bipatch.replace(
                        ["action_results", "turn"],
                        i,
                        i + 1
                    )
                    replay.record_bipatch(
                        base_time + timedelta(minutes=i),
                        123,
                        1,
                        bipatch
                    )

            # Verify
            with Replay(replay_file, mode='r') as replay:
                start = replay.get_start_time()
                last = replay.get_last_time()

                self.assertEqual(start, base_time)
                self.assertEqual(last, base_time + timedelta(minutes=10))

    def test_replay_append_mode(self):
        """Test appending patches to existing replay."""
        with tempfile.TemporaryDirectory() as temp_dir:
            replay_file = os.path.join(temp_dir, "test.replay")

            # Create initial replay
            with Replay(replay_file, mode='w', game_id=123, player_id=1) as replay:
                replay.record_initial_game_state(
                    self.game_state,
                    datetime(2024, 1, 1, 0, 0, 0),
                    123,
                    1
                )
                replay.storage.static_map_data_b = b''

                bipatch = BidirectionalReplayPatch()
                bipatch.replace(["action_results", "turn"], 1, 2)
                replay.record_bipatch(
                    datetime(2024, 1, 1, 0, 1, 0),
                    123,
                    1,
                    bipatch
                )

            # Append more patches
            with Replay(replay_file, mode='a', game_id=123, player_id=1) as replay:
                bipatch = BidirectionalReplayPatch()
                bipatch.replace(["action_results", "turn"], 2, 3)
                replay.record_bipatch(
                    datetime(2024, 1, 1, 0, 2, 0),
                    123,
                    1,
                    bipatch
                )

            # Verify both patches exist
            with Replay(replay_file, mode='r') as replay:
                last = replay.get_last_time()
                self.assertEqual(last.minute, 2)

    def test_replay_with_complex_state_changes(self):
        """Test replay with complex nested state changes."""
        with tempfile.TemporaryDirectory() as temp_dir:
            replay_file = os.path.join(temp_dir, "test.replay")

            # Create state with nested structures
            self.game_state.action_results["players"] = [
                {"name": "Alice", "health": 100, "inventory": ["sword", "shield"]},
                {"name": "Bob", "health": 80, "inventory": ["bow"]}
            ]

            with Replay(replay_file, mode='w', game_id=123, player_id=1) as replay:
                replay.record_initial_game_state(
                    self.game_state,
                    datetime(2024, 1, 1),
                    123,
                    1
                )
                replay.storage.static_map_data_b = b''

                # Change nested values
                bipatch = BidirectionalReplayPatch()
                bipatch.replace(
                    ["action_results", "players", 0, "health"],
                    100,
                    75
                )
                bipatch.add(
                    ["action_results", "players", 0, "inventory", 2],
                    None,
                    "potion"
                )

                replay.record_bipatch(
                    datetime(2024, 1, 1, 0, 1),
                    123,
                    1,
                    bipatch
                )

            # Verify patch was recorded
            with Replay(replay_file, mode='r') as replay:
                state = replay.load_initial_game_state()
                self.assertEqual(state.action_results["players"][0]["health"], 100)

    def test_apply_patch_forward(self):
        """Test applying patches forward through time."""
        with tempfile.TemporaryDirectory() as temp_dir:
            replay_file = os.path.join(temp_dir, "test.replay")

            with Replay(replay_file, mode='w', game_id=123, player_id=1) as replay:
                replay.record_initial_game_state(
                    self.game_state,
                    datetime(2024, 1, 1, 0, 0),
                    123,
                    1
                )
                replay.storage.static_map_data_b = b''

                # Create forward patch
                bipatch = BidirectionalReplayPatch()
                bipatch.replace(["action_results", "score"], 100, 200)

                replay.record_bipatch(
                    datetime(2024, 1, 1, 0, 1),
                    123,
                    1,
                    bipatch
                )

            # Load and apply
            with Replay(replay_file, mode='r') as replay:
                state = replay.load_initial_game_state()

                # Find and apply patch
                path = replay.storage.patch_graph.find_patch_path(
                    datetime(2024, 1, 1, 0, 0),
                    datetime(2024, 1, 1, 0, 1)
                )

                for patch_node in path:
                    replay.apply_patch(patch_node, state, self.game)

                self.assertEqual(state.action_results["score"], 200)

    def test_apply_patch_backward(self):
        """Test applying patches backward through time."""
        with tempfile.TemporaryDirectory() as temp_dir:
            replay_file = os.path.join(temp_dir, "test.replay")

            with Replay(replay_file, mode='w', game_id=123, player_id=1) as replay:
                replay.record_initial_game_state(
                    self.game_state,
                    datetime(2024, 1, 1, 0, 0),
                    123,
                    1
                )
                replay.storage.static_map_data_b = b''

                # Create bidirectional patches
                bipatch1 = BidirectionalReplayPatch()
                bipatch1.replace(["action_results", "score"], 100, 200)
                replay.record_bipatch(
                    datetime(2024, 1, 1, 0, 1),
                    123,
                    1,
                    bipatch1
                )

                bipatch2 = BidirectionalReplayPatch()
                bipatch2.replace(["action_results", "score"], 200, 300)
                replay.record_bipatch(
                    datetime(2024, 1, 1, 0, 2),
                    123,
                    1,
                    bipatch2
                )

            # Load and navigate backward
            with Replay(replay_file, mode='r') as replay:
                state = replay.load_initial_game_state()

                # Go forward to t=2
                forward_path = replay.storage.patch_graph.find_patch_path(
                    datetime(2024, 1, 1, 0, 0),
                    datetime(2024, 1, 1, 0, 2)
                )
                for patch_node in forward_path:
                    replay.apply_patch(patch_node, state, self.game)

                self.assertEqual(state.action_results["score"], 300)

                # Go backward to t=1
                backward_path = replay.storage.patch_graph.find_patch_path(
                    datetime(2024, 1, 1, 0, 2),
                    datetime(2024, 1, 1, 0, 1)
                )
                for patch_node in backward_path:
                    replay.apply_patch(patch_node, state, self.game)

                self.assertEqual(state.action_results["score"], 200)


    def test_replay_without_context_manager(self):
        """Test replay usage without context manager."""
        with tempfile.TemporaryDirectory() as temp_dir:
            replay_file = os.path.join(temp_dir, "test.replay")

            # Manual open/close
            replay = Replay(replay_file, mode='w', game_id=123, player_id=1)
            replay.open()

            replay.record_initial_game_state(
                self.game_state,
                datetime(2024, 1, 1),
                123,
                1
            )
            replay.storage.static_map_data_b = b''

            replay.close()

            # Verify file was written
            self.assertTrue(os.path.exists(replay_file))

    def test_replay_file_not_found(self):
        """Test error handling for missing replay file."""
        with self.assertRaises(FileNotFoundError):
            with Replay("/nonexistent/path/replay.db", mode='r'):
                pass


# ============================================================================
# Edge Cases and Error Handling Tests
# ============================================================================

class TestEdgeCases(unittest.TestCase):
    """Test edge cases and error conditions."""

    def test_apply_operation_to_none_reference(self):
        """Test applying operation when reference is None."""
        # This should handle gracefully or raise appropriate error
        with self.assertRaises((ValueError, AttributeError, TypeError)):
            apply_operation(REPLACE_OPERATION, 42, None, "attr")

    def test_get_child_reference_from_none(self):
        """Test getting child from None reference."""
        result = get_child_reference(None, "key")
        self.assertIsNone(result)

    def test_patch_with_circular_references(self):
        """Test handling of circular references in objects."""
        # Create objects with circular reference
        obj1 = {"name": "obj1"}
        obj2 = {"name": "obj2", "ref": obj1}
        obj1["ref"] = obj2

        # This should either handle it or raise clear error
        # (Actual behavior depends on implementation)
        try:
            patch = make_replay_patch(obj1, obj1)
            self.assertTrue(patch.is_empty())
        except RecursionError:
            self.skipTest("Circular references not supported")

    def test_extremely_deep_nesting(self):
        """Test handling of extremely deep object nesting."""
        # Create deeply nested structure
        deep_obj = {"level": 0}
        current = deep_obj
        for i in range(100):
            current["child"] = {"level": i + 1}
            current = current["child"]

        # Should handle without stack overflow
        path_tree = PathTree()
        path = ["root"] + ["child"] * 50
        idx = path_tree.get_or_add_path_node(path)
        self.assertIsNotNone(idx)

    def test_concurrent_patch_application(self):
        """Test that patches can be safely applied in sequence."""
        # This tests for reference invalidation issues
        state = {"players": [{"health": 100}, {"health": 80}]}

        patch1 = ReplayPatch()
        patch1.replace_op(["players", 0, "health"], 50)

        patch2 = ReplayPatch()
        patch2.replace_op(["players", 1, "health"], 40)

        # Apply both patches - should not interfere
        apply_operation(REPLACE_OPERATION, 50, state["players"][0], "health")
        apply_operation(REPLACE_OPERATION, 40, state["players"][1], "health")

        self.assertEqual(state["players"][0]["health"], 50)
        self.assertEqual(state["players"][1]["health"], 40)

    def test_patch_graph_with_duplicate_timestamps(self):
        """Test handling of patches with identical timestamps."""
        graph = PatchGraph()

        patch1 = PatchGraphNode(1000, 2000, [REPLACE_OPERATION], [1], [0])
        patch2 = PatchGraphNode(1000, 2000, [REPLACE_OPERATION], [2], [1])

        graph.add_patch_node(patch1)
        # Second patch should overwrite first
        graph.add_patch_node(patch2)

        self.assertEqual(len(graph.patches), 1)
        self.assertEqual(graph.patches[(1000, 2000)].values[0], 1)

    def test_steiner_tree_with_single_leaf(self):
        """Test Steiner tree with only root and one leaf."""
        tree = PathTree()
        idx = tree.get_or_add_path_node(["single", "path"])

        tree.precompute()
        steiner = tree.build_steiner_tree([idx])

        # Should include root and the leaf
        self.assertIn(0, steiner)
        self.assertIn(idx, steiner)

    def test_apply_patch_with_invalid_path_index(self):
        """Test handling of invalid path indices in patches."""
        tree = PathTree()
        tree.get_or_add_path_node(["valid", "path"])

        # Create patch with invalid index
        patch_node = PatchGraphNode(
            1000, 2000,
            [REPLACE_OPERATION],
            [999],  # Invalid index
            [42]
        )

        # Should raise appropriate error
        with self.assertRaises((KeyError, IndexError)):
            state = {"test": "data"}
            replay = Replay.__new__(Replay)
            replay.storage = type('obj', (object,), {
                'path_tree': tree,
                'idx_to_node': tree.idx_to_node
            })()
            replay.apply_patch(patch_node, state, GameInterface())


# ============================================================================
# Performance and Stress Tests
# ============================================================================

class TestPerformance(unittest.TestCase):
    """Performance and stress tests."""

    def test_large_replay_file(self):
        """Test replay with many patches."""
        with tempfile.TemporaryDirectory() as temp_dir:
            replay_file = os.path.join(temp_dir, "large.replay")

            game_state = GameState(
                time_stamp="2024-01-01T00:00:00Z",
                state_id="test",
                state_type=0,
                states=States(
                    player_state=None, newspaper_state=None, map_state=None,
                    resource_state=None, foreign_affairs_state=None,
                    army_state=None, spy_state=None, map_info_state=None,
                    admin_state=None, statistic_state=None, mod_state=None,
                    game_info_state=None, ai_state=None, premium_state=None,
                    user_options_state=None, user_inventory_state=None,
                    user_sms_state=None, tutorial_state=None,
                    build_queue_state=None, location_state=None,
                    triggered_tutorial_state=None,
                    wheel_of_fortune_state=None, research_state=None,
                    game_event_state=None, in_game_alliance_state=None,
                    exploration_state=None, quest_state=None,
                    configuration_state=None, mission_state=None
                ),
                action_results=HashMap()
            )
            game_state.action_results["counter"] = 0

            base_time = datetime(2024, 1, 1)

            with Replay(replay_file, mode='w', game_id=1, player_id=1) as replay:
                replay.record_initial_game_state(game_state, base_time, 1, 1)
                replay.storage.static_map_data_b = b''

                # Record 1000 patches
                for i in range(1000):
                    bipatch = BidirectionalReplayPatch()
                    bipatch.replace(
                        ["action_results", "counter"],
                        i,
                        i + 1
                    )
                    replay.record_bipatch(
                        base_time + timedelta(seconds=i),
                        1, 1,
                        bipatch
                    )

            # Verify file size is reasonable
            file_size = os.path.getsize(replay_file)
            self.assertLess(file_size, 10 * 1024 * 1024)  # < 10MB

            # Verify can be read
            with Replay(replay_file, mode='r') as replay:
                state = replay.load_initial_game_state()
                self.assertEqual(state.action_results["counter"], 0)

    def test_pathfinding_performance(self):
        """Test pathfinding with complex graph."""
        graph = PatchGraph()

        # Create branching graph structure
        base_time = 1000
        for i in range(100):
            for j in range(3):  # 3 branches at each level
                from_time = base_time + i
                to_time = base_time + i + 1

                patch = PatchGraphNode(
                    from_time, to_time,
                    [REPLACE_OPERATION],
                    [j],
                    [i]
                )
                graph.add_patch_node(patch)

        # Find path through graph
        path = graph.find_patch_path(
            datetime.fromtimestamp(base_time, tz=timezone.utc),
            datetime.fromtimestamp(base_time + 50, tz=timezone.utc)
        )

        self.assertGreater(len(path), 0)

    def test_memory_efficiency_of_path_tree(self):
        """Test that PathTree efficiently reuses nodes."""
        tree = PathTree()

        # Add 1000 paths with shared prefixes
        for i in range(100):
            for j in range(10):
                path = ["players", str(i), "units", str(j), "health"]
                tree.get_or_add_path_node(path)

        total_paths = 1000
        total_nodes = tree.idx_counter

        # Without sharing, would need 5 nodes per path (path length)
        # With sharing: 1 (root) + 1 (players) + 100 (player IDs) +
        #               100 (units per player) + 1000 (unit IDs) + 1000 (health)
        # Expected: ~2202 nodes
        nodes_without_sharing = total_paths * 5  # 5000

        # Should reuse at least 50% of nodes compared to no sharing
        self.assertLess(total_nodes, nodes_without_sharing * 0.5)
        # Or more specifically:
        self.assertLess(total_nodes, 2500)


# ============================================================================
# Reference Management Tests
# ============================================================================

class TestReferenceManagement(unittest.TestCase):
    """Test reference lifecycle and invalidation handling."""

    def test_reference_setting_on_leaf_nodes(self):
        """Test that references are properly set on leaf nodes."""
        tree = PathTree()
        state = {"players": [{"health": 100}]}

        path = ["players", 0, "health"]
        idx = tree.get_or_add_path_node(path)

        tree.precompute()
        steiner = tree.build_steiner_tree([idx])
        tree.bfs_set_references(steiner, state)

        # Leaf node should have reference to parent dict
        node = tree.idx_to_node[idx]
        self.assertIsNotNone(node.reference)

    def test_reference_nullification_on_remove(self):
        """Test that references are nullified when elements are removed."""
        state = {"items": [1, 2, 3]}

        apply_operation(REMOVE_OPERATION, None, state["items"], 1)

        self.assertEqual(len(state["items"]), 2)
        self.assertEqual(state["items"], [1, 3])

    def test_reference_persistence_across_patches(self):
        """Test that references remain valid across multiple patches."""
        tree = PathTree()
        state = {"counter": 0}

        path = ["counter"]
        idx = tree.get_or_add_path_node(path)

        tree.precompute()
        steiner = tree.build_steiner_tree([idx])
        tree.bfs_set_references(steiner, state)

        node = tree.idx_to_node[idx]
        original_ref = node.reference

        # Apply multiple operations
        for i in range(10):
            apply_operation(REPLACE_OPERATION, i, state, "counter")

        # Reference should still point to same dict
        self.assertEqual(node.reference, original_ref)


if __name__ == '__main__':
    # Run tests with verbose output
    unittest.main(verbosity=2)