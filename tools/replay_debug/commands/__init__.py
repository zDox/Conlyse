"""
Command modules for the Replay Debug CLI Tool.

This package organizes CLI commands into separate modules by category.
Import all command modules to ensure they are registered.
"""
from tools.replay_debug.commands import navigation_commands
from tools.replay_debug.commands import state_commands
from tools.replay_debug.commands import patch_commands
from tools.replay_debug.commands import advanced_commands

__all__ = [
    'navigation_commands',
    'state_commands',
    'patch_commands',
    'advanced_commands',
]
