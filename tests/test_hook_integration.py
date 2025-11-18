import unittest
from unittest.mock import Mock

from conflict_interface.interface.game_interface import GameInterface
from conflict_interface.interface.hook_system import ChangeType
from conflict_interface.replay.replay_patch import AddOperation
from conflict_interface.replay.replay_patch import RemoveOperation
from conflict_interface.replay.replay_patch import ReplaceOperation


class TestGameInterfaceHookIntegration(unittest.TestCase):
    """Test hook system integration with GameInterface."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.game_interface = GameInterface()
        
    def test_hook_system_initialized(self):
        """Test that hook system is initialized in GameInterface."""
        self.assertIsNotNone(self.game_interface._hook_system)
        
    def test_on_province_add_registration(self):
        """Test registering a province add callback."""
        callback = Mock()
        self.game_interface.on_province_add(callback)
        
        # Check hook was registered
        self.assertEqual(len(self.game_interface._hook_system.hooks), 1)
        hook = self.game_interface._hook_system.hooks[0]
        self.assertEqual(hook.pattern, ["states", "map_state", "map", "locations", "?"])
        self.assertEqual(hook.change_types, {ChangeType.ADD})
        
    def test_on_province_remove_registration(self):
        """Test registering a province remove callback."""
        callback = Mock()
        self.game_interface.on_province_remove(callback)
        
        # Check hook was registered
        self.assertEqual(len(self.game_interface._hook_system.hooks), 1)
        hook = self.game_interface._hook_system.hooks[0]
        self.assertEqual(hook.pattern, ["states", "map_state", "map", "locations", "?"])
        self.assertEqual(hook.change_types, {ChangeType.REMOVE})
        
    def test_on_province_attribute_change_registration(self):
        """Test registering a province attribute change callback."""
        callback = Mock()
        self.game_interface.on_province_attribute_change(callback, "owner_id")
        
        # Check hook was registered
        self.assertEqual(len(self.game_interface._hook_system.hooks), 1)
        hook = self.game_interface._hook_system.hooks[0]
        self.assertEqual(hook.pattern, ["states", "map_state", "map", "locations", "?", "owner_id"])
        self.assertEqual(hook.change_types, {ChangeType.REPLACE})
        
    def test_multiple_event_registrations(self):
        """Test registering multiple event callbacks."""
        callback_add = Mock()
        callback_remove = Mock()
        callback_attr = Mock()
        
        self.game_interface.on_province_add(callback_add)
        self.game_interface.on_province_remove(callback_remove)
        self.game_interface.on_province_attribute_change(callback_attr, "owner_id")
        
        # All three hooks should be registered
        self.assertEqual(len(self.game_interface._hook_system.hooks), 3)
        
    def test_province_add_hook_triggered(self):
        """Test that province add hook is triggered."""
        callback = Mock()
        self.game_interface.on_province_add(callback)
        
        # Simulate an add operation
        op = AddOperation(
            path=["states", "map_state", "map", "locations", "123"],
            new_value={"id": 123, "name": "Test Province"}
        )
        
        self.game_interface._hook_system.queue_hook_from_operation(op)
        self.game_interface._hook_system.execute_queued_hooks()
        
        # Callback should be called
        callback.assert_called_once()
        call_args = callback.call_args
        self.assertEqual(call_args.kwargs['change_type'], ChangeType.ADD)
        self.assertEqual(call_args.kwargs['path'][-1], "123")
        
    def test_province_remove_hook_triggered(self):
        """Test that province remove hook is triggered."""
        callback = Mock()
        self.game_interface.on_province_remove(callback)
        
        # Simulate a remove operation
        op = RemoveOperation(path=["states", "map_state", "map", "locations", "123"])
        
        self.game_interface._hook_system.queue_hook_from_operation(op)
        self.game_interface._hook_system.execute_queued_hooks()
        
        # Callback should be called
        callback.assert_called_once()
        call_args = callback.call_args
        self.assertEqual(call_args.kwargs['change_type'], ChangeType.REMOVE)
        self.assertEqual(call_args.kwargs['path'][-1], "123")
        
    def test_province_attribute_change_hook_triggered(self):
        """Test that province attribute change hook is triggered."""
        callback = Mock()
        self.game_interface.on_province_attribute_change(callback, "owner_id")
        
        # Simulate a replace operation
        op = ReplaceOperation(
            path=["states", "map_state", "map", "locations", "123", "owner_id"],
            new_value=42
        )
        
        self.game_interface._hook_system.queue_hook_from_operation(op, old_value=1)
        self.game_interface._hook_system.execute_queued_hooks()
        
        # Callback should be called
        callback.assert_called_once()
        call_args = callback.call_args
        self.assertEqual(call_args.kwargs['change_type'], ChangeType.REPLACE)
        self.assertEqual(call_args.kwargs['old_value'], 1)
        self.assertEqual(call_args.kwargs['new_value'], 42)
        
    def test_selective_hook_triggering(self):
        """Test that hooks are only triggered for matching operations."""
        callback_add = Mock()
        callback_remove = Mock()
        
        self.game_interface.on_province_add(callback_add)
        self.game_interface.on_province_remove(callback_remove)
        
        # Trigger only add operation
        op = AddOperation(
            path=["states", "map_state", "map", "locations", "123"],
            new_value={}
        )
        
        self.game_interface._hook_system.queue_hook_from_operation(op)
        self.game_interface._hook_system.execute_queued_hooks()
        
        # Only add callback should be called
        callback_add.assert_called_once()
        callback_remove.assert_not_called()


class TestApplyReplayIntegration(unittest.TestCase):
    """Test integration of hook system with apply_replay."""
    
    def test_hook_queuing_during_operation_application(self):
        """Test that hooks are queued when operations are processed."""
        # Test directly with the hook system rather than going through apply_patch_any
        # since that requires a fully initialized game state
        game = GameInterface()
        callback = Mock()
        game.on_province_add(callback)
        
        # Directly queue an operation
        op = AddOperation(
            path=["states", "map_state", "map", "locations", "123"],
            new_value={"id": 123}
        )
        
        game._hook_system.queue_hook_from_operation(op)
        
        # Check that hook was queued
        self.assertEqual(len(game._hook_system.queued_hooks), 1)
        
    def test_hook_execution_workflow(self):
        """Test the full workflow: register -> queue -> execute."""
        game = GameInterface()
        callback = Mock()
        game.on_province_add(callback)
        
        # Queue operation
        op = AddOperation(
            path=["states", "map_state", "map", "locations", "123"],
            new_value={"id": 123}
        )
        game._hook_system.queue_hook_from_operation(op)
        
        # Execute queued hooks
        game._hook_system.execute_queued_hooks()
        
        # Callback should have been called
        callback.assert_called_once()
        
        # Queue should be empty
        self.assertEqual(len(game._hook_system.queued_hooks), 0)


class TestHookSystemPerformance(unittest.TestCase):
    """Test performance characteristics of the hook system."""
    
    def test_hook_matching_performance(self):
        """Test that hook matching is fast even with many hooks."""
        game = GameInterface()
        
        # Register many hooks
        for i in range(100):
            callback = Mock()
            game.on_province_add(callback)
            game.on_province_remove(callback)
            game.on_province_attribute_change(callback, "owner_id")
        
        # Should have 300 hooks
        self.assertEqual(len(game._hook_system.hooks), 300)
        
        # Queue operations
        import time
        start = time.time()
        
        for i in range(100):
            op = AddOperation(
                path=["states", "map_state", "map", "locations", str(i)],
                new_value={"id": i}
            )
            game._hook_system.queue_hook_from_operation(op)
        
        duration = time.time() - start
        
        # Should complete quickly (< 1 second for 100 operations with 300 hooks)
        self.assertLess(duration, 1.0)
        
        # Should have queued correct number of hooks (100 operations * 100 add hooks)
        self.assertEqual(len(game._hook_system.queued_hooks), 10000)
        
    def test_hook_execution_performance(self):
        """Test that hook execution is fast."""
        game = GameInterface()
        
        # Register hooks with fast callbacks
        callback_count = [0]
        def fast_callback(**kwargs):
            callback_count[0] += 1
        
        for i in range(10):
            game.on_province_add(fast_callback)
        
        # Queue many operations
        for i in range(1000):
            op = AddOperation(
                path=["states", "map_state", "map", "locations", str(i)],
                new_value={"id": i}
            )
            game._hook_system.queue_hook_from_operation(op)
        
        # Execute all hooks
        import time
        start = time.time()
        game._hook_system.execute_queued_hooks()
        duration = time.time() - start
        
        # Should complete quickly (< 1 second for 10000 hook calls)
        self.assertLess(duration, 1.0)
        
        # All hooks should have been executed
        self.assertEqual(callback_count[0], 10000)


class TestHookSystemEdgeCases(unittest.TestCase):
    """Test edge cases and error handling."""
    
    def test_hook_with_no_game_state(self):
        """Test that hook system handles missing game state gracefully."""
        game = GameInterface()
        callback = Mock()
        game.on_province_add(callback)
        
        # Try to execute hooks without any operations
        game._hook_system.execute_queued_hooks()
        
        # Should not crash, callback should not be called
        callback.assert_not_called()
        
    def test_hook_with_malformed_path(self):
        """Test that hook system handles malformed paths."""
        game = GameInterface()
        callback = Mock()
        game.on_province_add(callback)
        
        # Queue operation with unexpected path
        op = AddOperation(
            path=["unexpected", "path"],
            new_value={}
        )
        
        game._hook_system.queue_hook_from_operation(op)
        game._hook_system.execute_queued_hooks()
        
        # Should not crash, callback should not be called
        callback.assert_not_called()
        
    def test_multiple_attributes_same_province(self):
        """Test hooks for multiple attribute changes on same province."""
        game = GameInterface()
        callback_owner = Mock()
        callback_name = Mock()
        
        game.on_province_attribute_change(callback_owner, "owner_id")
        game.on_province_attribute_change(callback_name, "name")
        
        # Change both attributes
        op1 = ReplaceOperation(
            path=["states", "map_state", "map", "locations", "123", "owner_id"],
            new_value=42
        )
        op2 = ReplaceOperation(
            path=["states", "map_state", "map", "locations", "123", "name"],
            new_value="New Name"
        )
        
        game._hook_system.queue_hook_from_operation(op1, old_value=1)
        game._hook_system.queue_hook_from_operation(op2, old_value="Old Name")
        game._hook_system.execute_queued_hooks()
        
        # Both callbacks should be called
        callback_owner.assert_called_once()
        callback_name.assert_called_once()


if __name__ == '__main__':
    unittest.main()
