"""
Test cases for make_bireplay_patch function.

This module tests the bidirectional replay patch creation functionality,
ensuring that patches can correctly represent forward and backward state transitions.
"""
import unittest
from dataclasses import dataclass
from typing import List
from typing import Optional

from conflict_interface.data_types.game_object import GameObject
from conflict_interface.data_types.custom_types import ProductionList
from conflict_interface.replay.make_bireplay_patch import make_bireplay_patch
from conflict_interface.replay.replay_patch import BidirectionalReplayPatch, ReplayPatch
from conflict_interface.data_types.game_object import dump_any

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
    units: List[MockUnit]
    score: int = 0

    MAPPING = {
        "name": "name",
        "units": "units",
        "score": "score",
    }


class TestMakeBireplayPatch(unittest.TestCase):
    """Test cases for make_bireplay_patch function."""

    def test_simple_value_change(self):
        """Test bidirectional patch creation for simple value changes."""
        unit1 = MockUnit(id=1, health=100)
        unit2 = MockUnit(id=1, health=75)

        bi_patch = make_bireplay_patch(unit1, unit2)

        # Verify it's a BidirectionalReplayPatch
        self.assertIsInstance(bi_patch, BidirectionalReplayPatch)

        # Verify forward patch has operations
        self.assertFalse(bi_patch.forward_patch.is_empty())

        # Verify backward patch has operations
        self.assertFalse(bi_patch.backward_patch.is_empty())

        self.assertEqual(bi_patch.forward_patch.operations[0].Key, "p")  # Replace operation
        self.assertEqual(bi_patch.forward_patch.operations[0].path, ['health'])
        self.assertEqual(bi_patch.forward_patch.operations[0].new_value, 75)

        self.assertEqual(bi_patch.backward_patch.operations[0].Key, "p")  # Replace operation
        self.assertEqual(bi_patch.backward_patch.operations[0].path, ['health'])
        self.assertEqual(bi_patch.backward_patch.operations[0].new_value, 100)

    def test_multiple_attribute_changes(self):
        """Test bidirectional patch for multiple attribute changes."""
        unit1 = MockUnit(id=1, health=100, position_x=10, position_y=20)
        unit2 = MockUnit(id=1, health=75, position_x=15, position_y=25)

        bi_patch = make_bireplay_patch(unit1, unit2)

        # Should have 3 replace operations (health, position_x, position_y changed)
        forward_ops = bi_patch.forward_patch.operations
        backward_ops = bi_patch.backward_patch.operations

        self.assertEqual(len(forward_ops), 3)
        self.assertEqual(len(backward_ops), 3)

        expected_forward = {'health': 75, 'position_x': 15, 'position_y': 25}
        expected_backward = {'health': 100, 'position_x': 10, 'position_y': 20}

        # Verify all operations are replace operations with correct structure
        for op in forward_ops:
            self.assertEqual(op.Key, "p")
            self.assertEqual(len(op.path), 1)
            self.assertIn(op.path[0], expected_forward)
            self.assertEqual(op.new_value, expected_forward[op.path[0]])

        for op in backward_ops:
            self.assertEqual(op.Key, "p")
            self.assertEqual(len(op.path), 1)
            self.assertIn(op.path[0], expected_backward)
            self.assertEqual(op.new_value, expected_backward[op.path[0]])

    def test_no_changes(self):
        """Test bidirectional patch when objects are identical."""
        unit1 = MockUnit(id=1, health=100)
        unit2 = MockUnit(id=1, health=100)

        bi_patch = make_bireplay_patch(unit1, unit2)

        # Both patches should be empty
        self.assertTrue(bi_patch.forward_patch.is_empty())
        self.assertTrue(bi_patch.backward_patch.is_empty())

    def test_list_add_operation(self):
        """Test bidirectional patch for list addition."""
        player1 = MockPlayer(name="Alice", units=[])
        player2 = MockPlayer(name="Alice", units=[MockUnit(id=1)])

        bi_patch = make_bireplay_patch(player1, player2)

        # Forward should have add operation, backward should have remove
        self.assertFalse(bi_patch.forward_patch.is_empty())
        self.assertFalse(bi_patch.backward_patch.is_empty())

        # Verify forward patch has add operation
        forward_ops = bi_patch.forward_patch.operations
        self.assertEqual(len(forward_ops), 1)
        self.assertEqual(forward_ops[0].Key, "a")  # Add operation
        self.assertEqual(forward_ops[0].path, ['units', 0])
        self.assertEqual(forward_ops[0].new_value, dump_any(MockUnit(id=1)))

        # Verify backward patch has remove operation
        backward_ops = bi_patch.backward_patch.operations
        self.assertEqual(len(backward_ops), 1)
        self.assertEqual(backward_ops[0].Key, "r")  # Remove operation
        self.assertEqual(backward_ops[0].path, ['units', 0])
        self.assertEqual(backward_ops[0].new_value, None)

    def test_list_remove_operation(self):
        """Test bidirectional patch for list removal."""
        player1 = MockPlayer(name="Alice", units=[MockUnit(id=1), MockUnit(id=2)])
        player2 = MockPlayer(name="Alice", units=[MockUnit(id=1)])

        bi_patch = make_bireplay_patch(player1, player2)

        # Forward should have remove operation, backward should have add
        self.assertFalse(bi_patch.forward_patch.is_empty())
        self.assertFalse(bi_patch.backward_patch.is_empty())

        # Verify forward patch has remove operation
        forward_ops = bi_patch.forward_patch.operations
        self.assertEqual(len(forward_ops), 1)
        self.assertEqual(forward_ops[0].Key, "r")  # Remove operation
        self.assertEqual(forward_ops[0].path, ['units', 1])
        self.assertEqual(forward_ops[0].new_value, None)

        # Verify backward patch has add operation
        backward_ops = bi_patch.backward_patch.operations
        self.assertEqual(len(backward_ops), 1)
        self.assertEqual(backward_ops[0].Key, "a")  # Add operation
        self.assertEqual(backward_ops[0].path, ['units', 1])
        self.assertEqual(backward_ops[0].new_value, dump_any(MockUnit(id=2)))

    def test_list_element_modification(self):
        """Test bidirectional patch for modifying list elements."""
        player1 = MockPlayer(name="Alice", units=[MockUnit(id=1, health=100)])
        player2 = MockPlayer(name="Alice", units=[MockUnit(id=1, health=50)])

        bi_patch = make_bireplay_patch(player1, player2)

        # Should have replace operation for the modified unit's health
        forward_ops = bi_patch.forward_patch.operations
        backward_ops = bi_patch.backward_patch.operations

        # Should have replace operation for the unit's health
        self.assertEqual(len(forward_ops), 1)
        self.assertEqual(forward_ops[0].Key, "p")  # Replace operation
        self.assertEqual(forward_ops[0].path, ['units', 0, 'health'])
        self.assertEqual(forward_ops[0].new_value, 50)

        self.assertEqual(len(backward_ops), 1)
        self.assertEqual(backward_ops[0].Key, "p")  # Replace operation
        self.assertEqual(backward_ops[0].path, ['units', 0, 'health'])
        self.assertEqual(backward_ops[0].new_value, 100)

    def test_dict_operations(self):
        """Test bidirectional patch for dictionary changes."""
        dict1 = {"key1": 100, "key2": 200}
        dict2 = {"key1": 150, "key3": 300}

        bi_patch = make_bireplay_patch(dict1, dict2)

        # Should have operations for replace (key1), add (key3), and remove (key2)
        self.assertFalse(bi_patch.forward_patch.is_empty())
        self.assertFalse(bi_patch.backward_patch.is_empty())

        forward_ops = bi_patch.forward_patch.operations
        backward_ops = bi_patch.backward_patch.operations

        # Verify we have 3 operations in each direction
        self.assertEqual(len(forward_ops), 3)
        self.assertEqual(len(backward_ops), 3)

        # Check each operation type exists with correct Key, path, and new_value
        forward_op_map = {tuple(op.path): op for op in forward_ops}
        backward_op_map = {tuple(op.path): op for op in backward_ops}

        # Forward: key1 replace
        self.assertIn(('key1',), forward_op_map)
        self.assertEqual(forward_op_map[('key1',)].Key, "p")
        self.assertEqual(forward_op_map[('key1',)].new_value, 150)

        # Forward: key3 add
        self.assertIn(('key3',), forward_op_map)
        self.assertEqual(forward_op_map[('key3',)].Key, "a")
        self.assertEqual(forward_op_map[('key3',)].new_value, 300)

        # Forward: key2 remove
        self.assertIn(('key2',), forward_op_map)
        self.assertEqual(forward_op_map[('key2',)].Key, "r")
        self.assertEqual(forward_op_map[('key2',)].new_value, None)

        # Backward: key1 replace
        self.assertIn(('key1',), backward_op_map)
        self.assertEqual(backward_op_map[('key1',)].Key, "p")
        self.assertEqual(backward_op_map[('key1',)].new_value, 100)

        # Backward: key3 remove
        self.assertIn(('key3',), backward_op_map)
        self.assertEqual(backward_op_map[('key3',)].Key, "r")
        self.assertEqual(backward_op_map[('key3',)].new_value, None)

        # Backward: key2 add
        self.assertIn(('key2',), backward_op_map)
        self.assertEqual(backward_op_map[('key2',)].Key, "a")
        self.assertEqual(backward_op_map[('key2',)].new_value, 200)

    def test_nested_object_changes(self):
        """Test bidirectional patch for nested object modifications."""
        player1 = MockPlayer(
            name="Bob",
            score=100,
            units=[MockUnit(id=1, health=100, position_x=0)]
        )
        player2 = MockPlayer(
            name="Bob",
            score=150,
            units=[MockUnit(id=1, health=80, position_x=5)]
        )

        bi_patch = make_bireplay_patch(player1, player2)

        # Should have operations for score and nested unit changes
        forward_ops = bi_patch.forward_patch.operations
        backward_ops = bi_patch.backward_patch.operations

        self.assertEqual(len(forward_ops), 3)  # score, health, position_x
        self.assertEqual(len(backward_ops), 3)

        # Verify each operation
        forward_op_map = {tuple(op.path): op for op in forward_ops}
        backward_op_map = {tuple(op.path): op for op in backward_ops}

        # Forward operations
        self.assertEqual(forward_op_map[('score',)].Key, "p")
        self.assertEqual(forward_op_map[('score',)].new_value, 150)

        self.assertEqual(forward_op_map[('units', 0, 'health')].Key, "p")
        self.assertEqual(forward_op_map[('units', 0, 'health')].new_value, 80)

        self.assertEqual(forward_op_map[('units', 0, 'position_x')].Key, "p")
        self.assertEqual(forward_op_map[('units', 0, 'position_x')].new_value, 5)

        # Backward operations
        self.assertEqual(backward_op_map[('score',)].Key, "p")
        self.assertEqual(backward_op_map[('score',)].new_value, 100)

        self.assertEqual(backward_op_map[('units', 0, 'health')].Key, "p")
        self.assertEqual(backward_op_map[('units', 0, 'health')].new_value, 100)

        self.assertEqual(backward_op_map[('units', 0, 'position_x')].Key, "p")
        self.assertEqual(backward_op_map[('units', 0, 'position_x')].new_value, 0)

    def test_symmetry(self):
        """Test that forward/backward patches are symmetric."""
        unit1 = MockUnit(id=1, health=100, position_x=10)
        unit2 = MockUnit(id=1, health=50, position_x=20)

        bi_patch = make_bireplay_patch(unit1, unit2)

        # The number of operations should be equal
        self.assertEqual(
            len(bi_patch.forward_patch.operations),
            len(bi_patch.backward_patch.operations)
        )

        # Each forward operation should have a corresponding backward operation
        forward_ops = bi_patch.forward_patch.operations
        backward_ops = bi_patch.backward_patch.operations

        forward_paths = {tuple(op.path) for op in forward_ops}
        backward_paths = {tuple(op.path) for op in backward_ops}

        self.assertEqual(forward_paths, backward_paths)

    def test_patch_serialization(self):
        """Test that bidirectional patches can be serialized."""
        unit1 = MockUnit(id=1, health=100)
        unit2 = MockUnit(id=1, health=75)

        bi_patch = make_bireplay_patch(unit1, unit2)

        # Test that patches can be converted to bytes
        forward_bytes = bi_patch.forward_patch.to_bytes()
        backward_bytes = bi_patch.backward_patch.to_bytes()

        self.assertIsInstance(forward_bytes, bytes)
        self.assertIsInstance(backward_bytes, bytes)

        # Test deserialization
        forward_restored = ReplayPatch.from_bytes(forward_bytes)
        backward_restored = ReplayPatch.from_bytes(backward_bytes)

        self.assertEqual(bi_patch.forward_patch, forward_restored)
        self.assertEqual(bi_patch.backward_patch, backward_restored)

    def test_empty_to_populated_list(self):
        """Test transition from empty to populated list."""
        player1 = MockPlayer(name="Charlie", units=[])
        player2 = MockPlayer(name="Charlie", units=[
            MockUnit(id=1, health=100),
            MockUnit(id=2, health=90),
        ])

        bi_patch = make_bireplay_patch(player1, player2)

        # Should have add operations
        self.assertFalse(bi_patch.forward_patch.is_empty())
        self.assertFalse(bi_patch.backward_patch.is_empty())

        forward_ops = bi_patch.forward_patch.operations
        backward_ops = bi_patch.backward_patch.operations

        self.assertEqual(len(forward_ops), 2)
        self.assertEqual(len(backward_ops), 2)

        # Verify forward adds
        self.assertEqual(forward_ops[0].Key, "a")
        self.assertEqual(forward_ops[0].path, ['units', 0])
        self.assertEqual(forward_ops[0].new_value, dump_any(MockUnit(id=1, health=100)))

        self.assertEqual(forward_ops[1].Key, "a")
        self.assertEqual(forward_ops[1].path, ['units', 1])
        self.assertEqual(forward_ops[1].new_value, dump_any(MockUnit(id=2, health=90)))

        print(bi_patch.backward_patch.debug_str())
        # Verify backward removes (in reverse order)
        self.assertEqual(backward_ops[0].Key, "r")
        self.assertEqual(backward_ops[0].path, ['units', 1])
        self.assertEqual(backward_ops[0].new_value, None)

        self.assertEqual(backward_ops[1].Key, "r")
        self.assertEqual(backward_ops[1].path, ['units', 0])
        self.assertEqual(backward_ops[1].new_value, None)

    def test_type_changes(self):
        """Test bidirectional patch when value types change."""
        obj1 = {"value": 100}
        obj2 = {"value": "string"}

        bi_patch = make_bireplay_patch(obj1, obj2)

        # Should handle type change with replace operation
        self.assertFalse(bi_patch.forward_patch.is_empty())
        self.assertFalse(bi_patch.backward_patch.is_empty())

        forward_ops = bi_patch.forward_patch.operations
        backward_ops = bi_patch.backward_patch.operations

        self.assertEqual(len(forward_ops), 1)
        self.assertEqual(forward_ops[0].Key, "p")
        self.assertEqual(forward_ops[0].path, ['value'])
        self.assertEqual(forward_ops[0].new_value, "string")

        self.assertEqual(len(backward_ops), 1)
        self.assertEqual(backward_ops[0].Key, "p")
        self.assertEqual(backward_ops[0].path, ['value'])
        self.assertEqual(backward_ops[0].new_value, 100)

    def test_none_to_value_transition(self):
        """Test transition from None to a value."""
        unit1 = MockUnit(id=1, health=100)
        unit2 = MockUnit(id=1, health=100)

        # Manually set an attribute to None (simulating Optional attribute)
        unit1.position_x = None
        unit2.position_x = 50

        bi_patch = make_bireplay_patch(unit1, unit2)

        # Should have replace operation for position_x
        self.assertFalse(bi_patch.forward_patch.is_empty())

        forward_ops = bi_patch.forward_patch.operations
        backward_ops = bi_patch.backward_patch.operations

        self.assertEqual(len(forward_ops), 1)
        self.assertEqual(forward_ops[0].Key, "p")
        self.assertEqual(forward_ops[0].path, ['position_x'])
        self.assertEqual(forward_ops[0].new_value, 50)

        self.assertEqual(len(backward_ops), 1)
        self.assertEqual(backward_ops[0].Key, "p")
        self.assertEqual(backward_ops[0].path, ['position_x'])
        self.assertEqual(backward_ops[0].new_value, None)

    def test_value_to_none_transition(self):
        """Test transition from a value to None."""
        unit1 = MockUnit(id=1, health=100, position_x=50)
        unit2 = MockUnit(id=1, health=100)
        unit2.position_x = None

        bi_patch = make_bireplay_patch(unit1, unit2)

        # Should have replace operation
        self.assertFalse(bi_patch.forward_patch.is_empty())

        forward_ops = bi_patch.forward_patch.operations
        backward_ops = bi_patch.backward_patch.operations

        self.assertEqual(len(forward_ops), 1)
        self.assertEqual(forward_ops[0].Key, "p")
        self.assertEqual(forward_ops[0].path, ['position_x'])
        self.assertEqual(forward_ops[0].new_value, None)

        self.assertEqual(len(backward_ops), 1)
        self.assertEqual(backward_ops[0].Key, "p")
        self.assertEqual(backward_ops[0].path, ['position_x'])
        self.assertEqual(backward_ops[0].new_value, 50)

    def test_complex_nested_changes(self):
        """Test complex scenario with multiple nested changes."""
        player1 = MockPlayer(
            name="Dave",
            score=1000,
            units=[
                MockUnit(id=1, health=100, position_x=0, position_y=0),
                MockUnit(id=2, health=90, position_x=10, position_y=10),
            ]
        )
        player2 = MockPlayer(
            name="Dave",
            score=1200,
            units=[
                MockUnit(id=1, health=80, position_x=5, position_y=5),
                MockUnit(id=2, health=90, position_x=10, position_y=10),
                MockUnit(id=3, health=100, position_x=20, position_y=20),
            ]
        )

        bi_patch = make_bireplay_patch(player1, player2)

        forward_ops = bi_patch.forward_patch.operations
        backward_ops = bi_patch.backward_patch.operations

        # Should have operations for:
        # - score change (1)
        # - unit 1: health, position_x, position_y changes (3)
        # - unit 3 addition (1)
        # Total: 5 operations
        self.assertEqual(len(forward_ops), 5)
        self.assertEqual(len(backward_ops), 5)

        forward_op_map = {tuple(op.path): op for op in forward_ops}
        backward_op_map = {tuple(op.path): op for op in backward_ops}

        # Verify score change
        self.assertEqual(forward_op_map[('score',)].Key, "p")
        self.assertEqual(forward_op_map[('score',)].new_value, 1200)
        self.assertEqual(backward_op_map[('score',)].Key, "p")
        self.assertEqual(backward_op_map[('score',)].new_value, 1000)

        # Verify unit 1 changes
        self.assertEqual(forward_op_map[('units', 0, 'health')].Key, "p")
        self.assertEqual(forward_op_map[('units', 0, 'health')].new_value, 80)
        self.assertEqual(backward_op_map[('units', 0, 'health')].Key, "p")
        self.assertEqual(backward_op_map[('units', 0, 'health')].new_value, 100)

        self.assertEqual(forward_op_map[('units', 0, 'position_x')].Key, "p")
        self.assertEqual(forward_op_map[('units', 0, 'position_x')].new_value, 5)
        self.assertEqual(backward_op_map[('units', 0, 'position_x')].Key, "p")
        self.assertEqual(backward_op_map[('units', 0, 'position_x')].new_value, 0)

        self.assertEqual(forward_op_map[('units', 0, 'position_y')].Key, "p")
        self.assertEqual(forward_op_map[('units', 0, 'position_y')].new_value, 5)
        self.assertEqual(backward_op_map[('units', 0, 'position_y')].Key, "p")
        self.assertEqual(backward_op_map[('units', 0, 'position_y')].new_value, 0)

        # Verify unit 3 addition/removal
        self.assertEqual(forward_op_map[('units', 2)].Key, "a")
        self.assertEqual(forward_op_map[('units', 2)].new_value,
                        dump_any(MockUnit(id=3, health=100, position_x=20, position_y=20)))
        self.assertEqual(backward_op_map[('units', 2)].Key, "r")
        self.assertEqual(backward_op_map[('units', 2)].new_value, None)