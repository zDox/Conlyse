"""
Test cases for apply_replay module.

This module tests the replay patch application functionality, including:
- Type extraction from list elements
- Path recursion through nested structures
- Patch application to game states
- Individual operation application (add, replace, remove)
"""
import unittest
from dataclasses import dataclass
from typing import Optional, Dict

from conflict_interface.data_types.game_object import GameObject, dump_any
from conflict_interface.data_types.game_state.game_state import GameState, States
from conflict_interface.interface.game_interface import GameInterface
from conflict_interface.data_types.custom_types import HashMap
from conflict_interface.replay.apply_replay import apply_operation
from conflict_interface.replay.apply_replay import apply_patch_any
from conflict_interface.replay.apply_replay import get_list_element_type
from conflict_interface.replay.apply_replay import recur_path
from conflict_interface.replay.replay_patch import AddOperation
from conflict_interface.replay.replay_patch import RemoveOperation
from conflict_interface.replay.replay_patch import ReplaceOperation
from conflict_interface.replay.replay_patch import ReplayPatch


# Mock GameObject classes for testing
@dataclass
class MockUnit(GameObject):
    """Mock unit class for testing."""
    C = "Unit"
    id: int
    health: int = 100
    position_x: Optional[int] = None
    position_y: Optional[int] = None

    MAPPING = {
        "id": "id",
        "health": "health",
        "position_x": "positionX",
        "position_y": "positionY",
    }


@dataclass
class MockPlayer(GameObject):
    """Mock player class for testing."""
    C = "Player"

    name: str
    units: list[MockUnit]
    score: int = 0
    resources: Optional[Dict[str, int]] = None

    MAPPING = {
        "name": "name",
        "units": "units",
        "score": "score",
        "resources": "resources",
    }



class TestGetListElementType(unittest.TestCase):
    """Test cases for get_list_element_type function."""

    def test_simple_list_type(self):
        """Test extracting type from simple List[int]."""
        list_element = 42
        list_type_hint = list[int]

        element_type = get_list_element_type(list_type_hint, list_element)
        self.assertEqual(element_type, int)

    def test_list_of_game_objects(self):
        """Test extracting type from List[GameObject]."""
        list_element = dump_any(MockUnit(id=1, health=100))
        list_type_hint = list[MockUnit]

        element_type = get_list_element_type(list_type_hint, list_element)
        self.assertEqual(element_type, MockUnit)

    def test_optional_list_type(self):
        """Test extracting type from Optional[List[int]]."""
        list_element = 42
        list_type_hint = Optional[list[int]]

        element_type = get_list_element_type(list_type_hint, list_element)
        self.assertEqual(element_type, int)


class TestRecurPath(unittest.TestCase):
    """Test cases for recur_path function."""

    def setUp(self):
        """Set up test fixtures."""
        self.game = GameInterface()
        # Create a simpler test structure using MockPlayer directly
        self.player = MockPlayer(
            name="TestPlayer",
            units=[MockUnit(id=1, health=100)],
            score=50
        )

    def test_simple_attribute_access(self):
        """Test accessing simple attribute."""
        obj, key, obj_type = recur_path(
            self.player,
            MockPlayer,
            ["name"],
            self.player,
            self.game
        )

        self.assertEqual(obj, self.player)
        self.assertEqual(key, "name")

    def test_nested_attribute_access(self):
        """Test accessing nested list element attribute."""
        obj, key, obj_type = recur_path(
            self.player,
            MockPlayer,
            ["units", 0, "health"],
            self.player,
            self.game
        )

        self.assertEqual(obj, self.player.units[0])
        self.assertEqual(key, "health")

    def test_list_element_access(self):
        """Test accessing list element."""
        obj, key, obj_type = recur_path(
            self.player,
            MockPlayer,
            ["units", 0],
            self.player,
            self.game
        )

        self.assertEqual(obj, self.player.units)
        self.assertEqual(key, 0)

    def test_invalid_path_raises_error(self):
        """Test that invalid path raises ValueError."""
        with self.assertRaises(ValueError):
            recur_path(
                self.player,
                MockPlayer,
                ["nonexistent"],
                self.player,
                self.game
            )

    def test_empty_path_raises_error(self):
        """Test that empty path raises ValueError."""
        with self.assertRaises(ValueError):
            recur_path(
                self.player,
                MockPlayer,
                [],
                self.player,
                self.game
            )


class TestApplyOperation(unittest.TestCase):
    """Test cases for apply_operation function."""

    def setUp(self):
        """Set up test fixtures."""
        self.game = GameInterface()

    def test_replace_on_game_object(self):
        """Test replace operation on GameObject attribute."""
        unit = MockUnit(id=1, health=100)
        op = ReplaceOperation(path=["health"], new_value=50)

        # Get the proper type hint for the health attribute
        obj_type = unit.get_type_hints_cached()["health"]
        apply_operation(op, unit, obj_type, "health", self.game)

        self.assertEqual(unit.health, 50)

    def test_replace_on_list_element(self):
        """Test replace operation on list element."""
        test_list = [10, 20, 30]
        op = ReplaceOperation(path=["1"], new_value=25)

        apply_operation(op, test_list, list[int], 1, self.game)

        self.assertEqual(test_list[1], 25)

    def test_replace_on_dict_value(self):
        """Test replace operation on dict value."""
        test_dict = {"key1": 100, "key2": 200}
        op = ReplaceOperation(path=["key1"], new_value=150)

        apply_operation(op, test_dict, Dict[str, int], "key1", self.game)

        self.assertEqual(test_dict["key1"], 150)

    def test_add_to_list(self):
        """Test add operation on list."""
        test_list = [10, 20]
        op = AddOperation(path=["2"], new_value=30)

        apply_operation(op, test_list, list[int], 2, self.game)

        self.assertEqual(len(test_list), 3)
        self.assertEqual(test_list[2], 30)

    def test_add_to_dict(self):
        """Test add operation on dict."""
        test_dict = {"key1": 100}
        op = AddOperation(path=["key2"], new_value=200)

        apply_operation(op, test_dict, Dict[str, int], "key2", self.game)

        self.assertEqual(test_dict["key2"], 200)

    def test_remove_from_game_object(self):
        """Test remove operation on GameObject attribute."""
        unit = MockUnit(id=1, health=100, position_x=50)
        op = RemoveOperation(path=["position_x"])

        apply_operation(op, unit, MockUnit, "position_x", self.game)

        self.assertIsNone(unit.position_x)

    def test_remove_from_list(self):
        """Test remove operation on list through full patch application."""
        # Use the full patch application path since apply_operation expects
        # proper type context from recur_path
        player = MockPlayer(name="Test", units=[MockUnit(id=1), MockUnit(id=2), MockUnit(id=3)], score=0)

        initial_len = len(player.units)
        op = RemoveOperation(path=["units", "1"])
        parent, pos, target_type = recur_path(
            player,
            MockPlayer,
            ["units", 1],
            player,
            self.game
        )
        apply_operation(op, parent, list, pos, self.game)

        self.assertEqual(len(player.units), initial_len - 1)
        self.assertEqual(player.units[0].id, 1)
        self.assertEqual(player.units[1].id, 3)

    def test_remove_from_dict(self):
        """Test remove operation on dict through full patch application."""
        # Use the full patch application path since apply_operation expects
        # proper type context from recur_path
        player = MockPlayer(name="Test", units=[], score=0)
        player.resources = {"key1": 100, "key2": 200}

        initial_len = len(player.resources)
        op = RemoveOperation(path=["resources", "key1"])
        parent, pos, target_type = recur_path(
            player,
            MockPlayer,
            ["resources", "key1"],
            player,
            self.game
        )
        apply_operation(op, parent, dict, pos, self.game)

        self.assertEqual(len(player.resources), initial_len - 1)
        self.assertEqual(player.resources.get("key1"), None)
        self.assertEqual(player.resources.get("key2"), 200)


class TestApplyPatchAny(unittest.TestCase):
    """Test cases for apply_patch_any function."""

    def setUp(self):
        """Set up test fixtures."""
        self.game = GameInterface()
        # Create a proper GameState with minimal required fields
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
        # Add custom test attributes for easier testing
        # We'll use the action_results HashMap for testing since it's a simple dict-like structure
        # Note: action_results is typed as HashMap[str, int]
        self.game_state.action_results["turn"] = 1
        self.game_state.action_results["score"] = 50
        self.game_state.action_results["level"] = 1

    def test_apply_simple_replace_patch(self):
        """Test applying simple replace patch."""
        patch = ReplayPatch()
        patch.replace_op(["action_results", "turn"], 2)

        apply_patch_any(patch, self.game_state, self.game)

        self.assertEqual(self.game_state.action_results["turn"], 2)


    def test_apply_multiple_operations(self):
        """Test applying patch with multiple operations."""
        patch = ReplayPatch()
        patch.replace_op(["action_results", "turn"], 2)
        patch.replace_op(["action_results", "score"], 100)
        patch.replace_op(["action_results", "level"], 3)

        apply_patch_any(patch, self.game_state, self.game)

        self.assertEqual(self.game_state.action_results["turn"], 2)
        self.assertEqual(self.game_state.action_results["score"], 100)
        self.assertEqual(self.game_state.action_results["level"], 3)

    def test_apply_add_operation_patch(self):
        """Test applying add operation patch."""
        patch = ReplayPatch()
        patch.add_op(["action_results", "new_key"], 999)

        apply_patch_any(patch, self.game_state, self.game)

        self.assertIn("new_key", self.game_state.action_results)
        self.assertEqual(self.game_state.action_results["new_key"], 999)

    def test_apply_remove_operation_patch(self):
        """Test applying remove operation patch."""
        # Add a key first
        self.game_state.action_results["temp_key"] = 123

        patch = ReplayPatch()
        patch.remove_op(["action_results", "temp_key"])

        apply_patch_any(patch, self.game_state, self.game)

        self.assertNotIn("temp_key", self.game_state.action_results)

    def test_apply_complex_patch(self):
        """Test applying complex patch with mixed operations."""
        patch = ReplayPatch()
        # Replace operations
        patch.replace_op(["action_results", "turn"], 5)
        patch.replace_op(["action_results", "score"], 200)
        # Add operation
        patch.add_op(["action_results", "gold"], 1000)
        # Another replace
        patch.replace_op(["action_results", "level"], 10)

        apply_patch_any(patch, self.game_state, self.game)

        self.assertEqual(self.game_state.action_results["turn"], 5)
        self.assertEqual(self.game_state.action_results["score"], 200)
        self.assertEqual(self.game_state.action_results["gold"], 1000)
        self.assertEqual(self.game_state.action_results["level"], 10)

    def test_apply_empty_patch(self):
        """Test applying empty patch has no effect."""
        original_turn = self.game_state.action_results["turn"]
        original_score = self.game_state.action_results["score"]

        patch = ReplayPatch()

        apply_patch_any(patch, self.game_state, self.game)

        self.assertEqual(self.game_state.action_results["turn"], original_turn)
        self.assertEqual(self.game_state.action_results["score"], original_score)

    def test_apply_patch_raises_on_non_game_state(self):
        """Test that applying patch to non-GameState raises ValueError."""
        patch = ReplayPatch()
        patch.replace_op(["score"], 100)

        # Try to apply to a non-GameState object
        player = MockPlayer(name="Test", units=[], score=50)
        with self.assertRaises(ValueError):
            apply_patch_any(patch, player, self.game)