import unittest
from unittest.mock import Mock

from conflict_interface.interface.game_interface import GameInterface
from conflict_interface.hook_system import ChangeType
from conflict_interface.replay.replay_patch import AddOperation
from conflict_interface.replay.replay_patch import ReplaceOperation


class TestGameInterfaceHookIntegration(unittest.TestCase):
    """Test hook system integration with GameInterface."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.game_interface = GameInterface()
        
    def test_hook_system_initialized(self):
        """Test that hook system is initialized in GameInterface."""
        self.assertIsNotNone(self.game_interface._hook_system)
        
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
        callback_attr_owner = Mock()
        callback_attr_resource_production = Mock()


        self.game_interface.on_province_attribute_change(callback_attr_owner, "owner_id")
        self.game_interface.on_province_attribute_change(callback_attr_resource_production, "resource_production")

        
        # All two hooks should be registered
        self.assertEqual(len(self.game_interface._hook_system.hooks), 2)




class TestApplyReplayIntegration(unittest.TestCase):
    """Test integration of hook system with apply_replay."""
    
    def test_hook_queuing_during_operation_application(self):
        """Test that hooks are queued when operations are processed."""
        # Test directly with the hook system rather than going through apply_patch_any
        # since that requires a fully initialized game state
        game = GameInterface()
        callback = Mock()
        game.on_province_attribute_change(callback, "owner_id")
        
        # Directly queue an operation
        op = ReplaceOperation(
            path=["states", "map_state", "map", "locations", "123", "owner_id"],
            new_value=12,
        )
        
        game._hook_system.queue_hook_from_operation(op)
        
        # Check that hook was queued
        self.assertEqual(len(game._hook_system.queued_hooks), 1)



class TestHookSystemEdgeCases(unittest.TestCase):
    """Test edge cases and error handling."""
    
    def test_hook_with_no_game_state(self):
        """Test that hook system handles missing game state gracefully."""
        game = GameInterface()
        callback = Mock()
        game.on_province_attribute_change(callback, "owner_id")
        
        # Try to execute hooks without any operations
        game._hook_system.execute_queued_hooks()
        
        # Should not crash, callback should not be called
        callback.assert_not_called()
        
    def test_hook_with_malformed_path(self):
        """Test that hook system handles malformed paths."""
        game = GameInterface()
        callback = Mock()
        game.on_province_attribute_change(callback, "owner_id")
        
        # Queue operation with unexpected path
        op = AddOperation(
            path=["unexpected", "path"],
            new_value={}
        )
        
        game._hook_system.queue_hook_from_operation(op)
        game._hook_system.execute_queued_hooks()
        
        # Should not crash, callback should not be called
        callback.assert_not_called()

if __name__ == '__main__':
    unittest.main()
