"""
Advanced commands for the Replay Debug CLI Tool.

This module defines advanced commands for power users:
- ritf: Show ReplayInterface information
- python: Enter Python REPL with ritf available
"""
from tools.replay_debug.command_registry import command


@command(
    name="ritf",
    description="Show ReplayInterface information",
    usage="ritf"
)
def cmd_ritf(cli):
    """Show ReplayInterface info."""
    ritf = cli.ritf
    if ritf:
        print("\nReplayInterface object is available as 'ritf'")
        print(f"Type: {type(ritf)}")
        try:
            print(f"Current time: {ritf.current_time}")
            print(f"Game ID: {ritf.game_id}")
            print(f"Player ID: {ritf.player_id}")
            print("\nYou can access:")
            print("  ritf.game_state - Current game state")
            print("  ritf.jump_to(datetime) - Jump to timestamp")
            print("  ritf.jump_to_next_patch() - Jump forward")
            print("  ritf.jump_to_previous_patch() - Jump backward")
            print("  ritf.get_timestamps() - Get all timestamps")
        except AttributeError as e:
            print(f"\nWarning: Some attributes not available: {e}")
    else:
        print("Error: ritf not available")


@command(
    name="python",
    description="Enter Python REPL with ritf available",
    usage="python"
)
def cmd_python(cli):
    """Enter Python REPL with ritf."""
    ritf = cli.ritf
    print("\nEntering Python REPL. 'ritf' is available.")
    print("Use Ctrl-D (Unix) or Ctrl-Z (Windows) to exit.\n")
    try:
        import code
        code.interact(local={'ritf': ritf, 'cli': cli})
    except Exception as e:
        print(f"Error: {e}")
