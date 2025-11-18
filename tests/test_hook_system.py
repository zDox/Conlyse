import unittest
from unittest.mock import Mock

from conflict_interface.hook_system import HookSystem, ChangeType, HookRegistration
from conflict_interface.replay.replay_patch import AddOperation, RemoveOperation, ReplaceOperation


class TestHookRegistration(unittest.TestCase):
    """Test HookRegistration matching logic."""
    
    def test_exact_match(self):
        """Test exact path matching without wildcards."""
        hook = HookRegistration(
            pattern=["states", "map_state", "map", "provinces"],
            callback=Mock(),
            change_types={ChangeType.ADD}
        )
        
        # Should match exact path
        self.assertTrue(hook.matches(["states", "map_state", "map", "provinces"], ChangeType.ADD))
        
        # Should not match different path
        self.assertFalse(hook.matches(["states", "map_state", "map", "cities"], ChangeType.ADD))
        
        # Should not match wrong change type
        self.assertFalse(hook.matches(["states", "map_state", "map", "provinces"], ChangeType.REMOVE))
        
    def test_wildcard_match(self):
        """Test wildcard matching with ?."""
        hook = HookRegistration(
            pattern=["states", "map_state", "map", "provinces", "?"],
            callback=Mock(),
            change_types={ChangeType.ADD, ChangeType.REMOVE}
        )
        
        # Should match any province id
        self.assertTrue(hook.matches(["states", "map_state", "map", "provinces", "123"], ChangeType.ADD))
        self.assertTrue(hook.matches(["states", "map_state", "map", "provinces", "456"], ChangeType.REMOVE))
        
        # Should not match shorter path
        self.assertFalse(hook.matches(["states", "map_state", "map", "provinces"], ChangeType.ADD))
        
        # Should match longer path (hook pattern is prefix)
        self.assertTrue(hook.matches(["states", "map_state", "map", "provinces", "123", "owner_id"], ChangeType.ADD))
        
    def test_attribute_match(self):
        """Test matching specific attributes."""
        hook = HookRegistration(
            pattern=["states", "map_state", "map", "provinces", "?", "owner_id"],
            callback=Mock(),
            change_types={ChangeType.REPLACE}
        )
        
        # Should match attribute change
        self.assertTrue(hook.matches(
            ["states", "map_state", "map", "provinces", "123", "owner_id"], 
            ChangeType.REPLACE
        ))
        
        # Should not match different attribute
        self.assertFalse(hook.matches(
            ["states", "map_state", "map", "provinces", "123", "name"], 
            ChangeType.REPLACE
        ))
        
        # Should not match wrong change type
        self.assertFalse(hook.matches(
            ["states", "map_state", "map", "provinces", "123", "owner_id"], 
            ChangeType.ADD
        ))
        
    def test_multiple_wildcards(self):
        """Test multiple wildcards in pattern."""
        hook = HookRegistration(
            pattern=["states", "?", "?", "provinces", "?"],
            callback=Mock(),
            change_types={ChangeType.ADD}
        )
        
        # Should match with any values for wildcards
        self.assertTrue(hook.matches(
            ["states", "map_state", "map", "provinces", "123"], 
            ChangeType.ADD
        ))
        self.assertTrue(hook.matches(
            ["states", "army_state", "armies", "provinces", "456"], 
            ChangeType.ADD
        ))
        
    def test_pattern_longer_than_path(self):
        """Test that pattern longer than path doesn't match."""
        hook = HookRegistration(
            pattern=["states", "map_state", "map", "provinces", "?", "owner_id"],
            callback=Mock(),
            change_types={ChangeType.ADD}
        )
        
        # Pattern is longer than path, should not match
        self.assertFalse(hook.matches(["states", "map_state", "map", "provinces"], ChangeType.ADD))


class TestHookSystem(unittest.TestCase):
    """Test HookSystem functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.hook_system = HookSystem()
        
    def test_register_hook(self):
        """Test registering a hook."""
        callback = Mock()
        self.hook_system.register_hook(
            "states.map_state.map.provinces.?",
            callback,
            {ChangeType.ADD}
        )
        
        self.assertEqual(len(self.hook_system.hooks), 1)
        hook = self.hook_system.hooks[0]
        self.assertEqual(hook.pattern, ["states", "map_state", "map", "provinces", "?"])
        self.assertEqual(hook.callback, callback)
        self.assertEqual(hook.change_types, {ChangeType.ADD})
        
    def test_register_hook_default_change_types(self):
        """Test registering a hook with default change types."""
        callback = Mock()
        self.hook_system.register_hook("states.map_state.map.provinces.?", callback)
        
        hook = self.hook_system.hooks[0]
        self.assertEqual(hook.change_types, {ChangeType.ADD, ChangeType.REMOVE, ChangeType.REPLACE})
        
    def test_queue_hook_from_add_operation(self):
        """Test queuing hooks from AddOperation."""
        callback = Mock()
        self.hook_system.register_hook(
            "states.map_state.map.provinces.?",
            callback,
            {ChangeType.ADD}
        )
        
        op = AddOperation(
            path=["states", "map_state", "map", "provinces", "123"],
            new_value={"id": 123, "name": "Test Province"}
        )
        
        self.hook_system.queue_hook_from_operation(op)
        
        self.assertEqual(len(self.hook_system.queued_hooks), 1)
        queued = self.hook_system.queued_hooks[0]
        self.assertEqual(queued.change_type, ChangeType.ADD)
        self.assertEqual(queued.path, ["states", "map_state", "map", "provinces", "123"])
        self.assertEqual(queued.new_value, {"id": 123, "name": "Test Province"})
        
    def test_queue_hook_from_remove_operation(self):
        """Test queuing hooks from RemoveOperation."""
        callback = Mock()
        self.hook_system.register_hook(
            "states.map_state.map.provinces.?",
            callback,
            {ChangeType.REMOVE}
        )
        
        op = RemoveOperation(path=["states", "map_state", "map", "provinces", "123"])
        
        self.hook_system.queue_hook_from_operation(op)
        
        self.assertEqual(len(self.hook_system.queued_hooks), 1)
        queued = self.hook_system.queued_hooks[0]
        self.assertEqual(queued.change_type, ChangeType.REMOVE)
        self.assertEqual(queued.new_value, None)
        
    def test_queue_hook_from_replace_operation(self):
        """Test queuing hooks from ReplaceOperation."""
        callback = Mock()
        self.hook_system.register_hook(
            "states.map_state.map.provinces.?.owner_id",
            callback,
            {ChangeType.REPLACE}
        )
        
        op = ReplaceOperation(
            path=["states", "map_state", "map", "provinces", "123", "owner_id"],
            new_value=42
        )
        
        self.hook_system.queue_hook_from_operation(op, old_value=1)
        
        self.assertEqual(len(self.hook_system.queued_hooks), 1)
        queued = self.hook_system.queued_hooks[0]
        self.assertEqual(queued.change_type, ChangeType.REPLACE)
        self.assertEqual(queued.old_value, 1)
        self.assertEqual(queued.new_value, 42)
        
    def test_multiple_matching_hooks(self):
        """Test that multiple hooks can match the same operation."""
        callback1 = Mock()
        callback2 = Mock()
        
        # Register two hooks that both match
        self.hook_system.register_hook(
            "states.map_state.map.provinces.?",
            callback1,
            {ChangeType.ADD}
        )
        self.hook_system.register_hook(
            "states.map_state.map.provinces.?",
            callback2,
            {ChangeType.ADD}
        )
        
        op = AddOperation(
            path=["states", "map_state", "map", "provinces", "123"],
            new_value={"id": 123}
        )
        
        self.hook_system.queue_hook_from_operation(op)
        
        # Both hooks should be queued
        self.assertEqual(len(self.hook_system.queued_hooks), 2)
        
    def test_no_matching_hooks(self):
        """Test that non-matching operations don't queue hooks."""
        callback = Mock()
        self.hook_system.register_hook(
            "states.map_state.map.provinces.?",
            callback,
            {ChangeType.ADD}
        )
        
        # Different path
        op = AddOperation(
            path=["states", "army_state", "armies", "123"],
            new_value={}
        )
        
        self.hook_system.queue_hook_from_operation(op)
        
        self.assertEqual(len(self.hook_system.queued_hooks), 0)
        
    def test_execute_queued_hooks(self):
        """Test executing queued hooks."""
        callback = Mock()
        self.hook_system.register_hook(
            "states.map_state.map.provinces.?",
            callback,
            {ChangeType.ADD}
        )
        
        op = AddOperation(
            path=["states", "map_state", "map", "provinces", "123"],
            new_value={"id": 123}
        )
        
        self.hook_system.queue_hook_from_operation(op)
        self.hook_system.execute_queued_hooks()
        
        # Callback should be called once
        callback.assert_called_once()
        
        # Queue should be empty after execution
        self.assertEqual(len(self.hook_system.queued_hooks), 0)
        
        # Check callback arguments
        call_args = callback.call_args
        self.assertEqual(call_args.kwargs['change_type'], ChangeType.ADD)
        self.assertEqual(call_args.kwargs['path'], ["states", "map_state", "map", "provinces", "123"])
        self.assertEqual(call_args.kwargs['new_value'], {"id": 123})
        
    def test_execute_multiple_hooks(self):
        """Test executing multiple queued hooks."""
        callback1 = Mock()
        callback2 = Mock()
        
        self.hook_system.register_hook(
            "states.map_state.map.provinces.?",
            callback1,
            {ChangeType.ADD}
        )
        self.hook_system.register_hook(
            "states.map_state.map.provinces.?",
            callback2,
            {ChangeType.REMOVE}
        )
        
        # Queue two operations
        op1 = AddOperation(
            path=["states", "map_state", "map", "provinces", "123"],
            new_value={"id": 123}
        )
        op2 = RemoveOperation(path=["states", "map_state", "map", "provinces", "456"])
        
        self.hook_system.queue_hook_from_operation(op1)
        self.hook_system.queue_hook_from_operation(op2)
        
        self.hook_system.execute_queued_hooks()
        
        # Both callbacks should be called
        callback1.assert_called_once()
        callback2.assert_called_once()
        
    def test_hook_exception_handling(self):
        """Test that exceptions in hooks don't break execution."""
        callback1 = Mock(side_effect=Exception("Test error"))
        callback2 = Mock()
        
        self.hook_system.register_hook(
            "states.map_state.map.provinces.?",
            callback1,
            {ChangeType.ADD}
        )
        self.hook_system.register_hook(
            "states.map_state.map.provinces.?",
            callback2,
            {ChangeType.ADD}
        )
        
        op = AddOperation(
            path=["states", "map_state", "map", "provinces", "123"],
            new_value={"id": 123}
        )
        
        self.hook_system.queue_hook_from_operation(op)
        
        # Should not raise exception
        self.hook_system.execute_queued_hooks()
        
        # Both callbacks should be attempted
        callback1.assert_called_once()
        callback2.assert_called_once()
        
    def test_clear_hooks(self):
        """Test clearing all hooks."""
        callback = Mock()
        self.hook_system.register_hook("states.map_state.map.provinces.?", callback)
        
        self.assertEqual(len(self.hook_system.hooks), 1)
        
        self.hook_system.clear_hooks()
        
        self.assertEqual(len(self.hook_system.hooks), 0)
        
    def test_clear_queue(self):
        """Test clearing queued hooks without executing."""
        callback = Mock()
        self.hook_system.register_hook(
            "states.map_state.map.provinces.?",
            callback,
            {ChangeType.ADD}
        )
        
        op = AddOperation(
            path=["states", "map_state", "map", "provinces", "123"],
            new_value={}
        )
        
        self.hook_system.queue_hook_from_operation(op)
        self.assertEqual(len(self.hook_system.queued_hooks), 1)
        
        self.hook_system.clear_queue()
        
        self.assertEqual(len(self.hook_system.queued_hooks), 0)
        callback.assert_not_called()


class TestHookPatterns(unittest.TestCase):
    """Test various hook patterns."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.hook_system = HookSystem()
        
    def test_province_add_pattern(self):
        """Test pattern for province additions."""
        callback = Mock()
        self.hook_system.register_hook(
            "states.map_state.map.provinces.?",
            callback,
            {ChangeType.ADD}
        )
        
        op = AddOperation(
            path=["states", "map_state", "map", "provinces", "123"],
            new_value={"id": 123}
        )
        
        self.hook_system.queue_hook_from_operation(op)
        self.hook_system.execute_queued_hooks()
        
        callback.assert_called_once()
        
    def test_province_remove_pattern(self):
        """Test pattern for province removals."""
        callback = Mock()
        self.hook_system.register_hook(
            "states.map_state.map.provinces.?",
            callback,
            {ChangeType.REMOVE}
        )
        
        op = RemoveOperation(path=["states", "map_state", "map", "provinces", "123"])
        
        self.hook_system.queue_hook_from_operation(op)
        self.hook_system.execute_queued_hooks()
        
        callback.assert_called_once()
        
    def test_province_attribute_change_pattern(self):
        """Test pattern for province attribute changes."""
        callback = Mock()
        self.hook_system.register_hook(
            "states.map_state.map.provinces.?.owner_id",
            callback,
            {ChangeType.REPLACE}
        )
        
        op = ReplaceOperation(
            path=["states", "map_state", "map", "provinces", "123", "owner_id"],
            new_value=42
        )
        
        self.hook_system.queue_hook_from_operation(op, old_value=1)
        self.hook_system.execute_queued_hooks()
        
        callback.assert_called_once()
        call_args = callback.call_args
        self.assertEqual(call_args.kwargs['old_value'], 1)
        self.assertEqual(call_args.kwargs['new_value'], 42)
        
    def test_any_attribute_change_pattern(self):
        """Test pattern for any attribute change on an object."""
        callback = Mock()
        self.hook_system.register_hook(
            "states.map_state.map.provinces.?.?",
            callback,
            {ChangeType.REPLACE}
        )
        
        # Should match any attribute
        op1 = ReplaceOperation(
            path=["states", "map_state", "map", "provinces", "123", "owner_id"],
            new_value=42
        )
        op2 = ReplaceOperation(
            path=["states", "map_state", "map", "provinces", "123", "name"],
            new_value="New Name"
        )
        
        self.hook_system.queue_hook_from_operation(op1)
        self.hook_system.queue_hook_from_operation(op2)
        self.hook_system.execute_queued_hooks()
        
        self.assertEqual(callback.call_count, 2)


if __name__ == '__main__':
    unittest.main()
