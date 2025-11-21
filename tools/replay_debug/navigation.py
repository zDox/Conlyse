"""
Navigation utilities for replay time travel.

This module provides functionality for jumping to different points in the replay:
- Jump by relative time (e.g., +5 seconds, -10 minutes)
- Jump by absolute time (specific timestamp)
- Jump by number of patches (e.g., +5 patches forward, -3 patches backward)
- Jump by timestamp index
"""
from datetime import datetime, timedelta, UTC
from typing import Optional, Tuple
from conflict_interface.interface.replay_interface import ReplayInterface


class ReplayNavigator:
    """Handles navigation through replay timestamps."""
    
    def __init__(self, replay_interface: ReplayInterface):
        """Initialize the navigator with a replay interface.
        
        Args:
            replay_interface: The ReplayInterface instance to navigate
        """
        self.ritf = replay_interface
    
    def jump_by_relative_time(self, seconds: float) -> bool:
        """Jump by a relative amount of time from current position.
        
        Args:
            seconds: Number of seconds to jump (positive for forward, negative for backward)
            
        Returns:
            True if successful, False if out of bounds
        """
        current_time = self.ritf.current_time
        target_time = current_time + timedelta(seconds=seconds)
        
        # Clamp to valid range
        if target_time < self.ritf.start_time:
            target_time = self.ritf.start_time
        elif target_time > self.ritf.end_time:
            target_time = self.ritf.end_time
        
        try:
            self.ritf.jump_to(target_time)
            return True
        except Exception as e:
            print(f"Error jumping to time: {e}")
            return False
    
    def jump_to_absolute_time(self, timestamp: datetime) -> bool:
        """Jump to an absolute timestamp.
        
        Args:
            timestamp: The datetime to jump to
            
        Returns:
            True if successful, False if out of bounds
        """
        # Clamp to valid range
        if timestamp < self.ritf.start_time:
            timestamp = self.ritf.start_time
        elif timestamp > self.ritf.end_time:
            timestamp = self.ritf.end_time
        
        try:
            self.ritf.jump_to(timestamp)
            return True
        except Exception as e:
            print(f"Error jumping to time: {e}")
            return False
    
    def jump_by_patches(self, num_patches: int) -> bool:
        """Jump forward or backward by a number of patches.
        
        Args:
            num_patches: Number of patches to jump (positive for forward, negative for backward)
            
        Returns:
            True if successful, False if out of bounds
        """
        if num_patches == 0:
            return True
        
        try:
            if num_patches > 0:
                # Jump forward
                for _ in range(num_patches):
                    if not self.ritf.jump_to_next_patch():
                        return False
            else:
                # Jump backward
                for _ in range(abs(num_patches)):
                    if not self.ritf.jump_to_previous_patch():
                        return False
            return True
        except Exception as e:
            print(f"Error jumping by patches: {e}")
            return False
    
    def jump_to_timestamp_index(self, index: int) -> bool:
        """Jump to a specific timestamp by its index.
        
        Args:
            index: 0-based index of the timestamp
            
        Returns:
            True if successful, False if index out of range
        """
        timestamps = self.ritf.get_timestamps()
        
        if index < 0 or index >= len(timestamps):
            print(f"Error: Index {index} out of range (0-{len(timestamps)-1})")
            return False
        
        try:
            self.ritf.jump_to(timestamps[index])
            return True
        except Exception as e:
            print(f"Error jumping to index: {e}")
            return False
    
    def list_timestamps(self, limit: int = 50) -> None:
        """List all timestamps with their indices.
        
        Args:
            limit: Maximum number of timestamps to display
        """
        timestamps = self.ritf.get_timestamps()
        current_idx = self.ritf.current_timestamp_index
        
        print(f"\nTotal timestamps: {len(timestamps)}")
        print(f"Current index: {current_idx}")
        print(f"Showing {'all' if len(timestamps) <= limit else f'first {limit}'} timestamps:\n")
        print(f"{'Index':<8} {'Timestamp':<30} {'Current':<8}")
        print("-" * 50)
        
        for i, ts in enumerate(timestamps[:limit]):
            is_current = ">>>" if i == current_idx else ""
            print(f"{i:<8} {ts.isoformat():<30} {is_current:<8}")
        
        if len(timestamps) > limit:
            print(f"\n... and {len(timestamps) - limit} more timestamps")
    
    def get_current_position_info(self) -> Tuple[int, datetime, datetime, datetime]:
        """Get information about current position in replay.
        
        Returns:
            Tuple of (index, current_time, start_time, end_time)
        """
        return (
            self.ritf.current_timestamp_index,
            self.ritf.current_time,
            self.ritf.start_time,
            self.ritf.end_time
        )
