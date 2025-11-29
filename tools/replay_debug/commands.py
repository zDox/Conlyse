"""
Command definitions for the Replay Debug CLI Tool.

This module defines all CLI commands using the @command decorator.
Each command is automatically registered in the CommandRegistry.
"""
from tools.replay_debug.command_registry import command, arg, ArgType
from tools.replay_debug.constants import DEFAULT_LIMIT, DEFAULT_DIRECTION


# ===== Navigation Commands =====

@command(
    name="info",
    description="Display current replay position and metadata",
    usage="info"
)
def cmd_info(cli):
    """Display current replay position and metadata."""
    cli.display_info()


@command(
    name="jump-relative",
    aliases=["jr"],
    description="Jump by relative time",
    usage="jump-relative <seconds> | jr <seconds>",
    arguments=[
        arg(name="seconds", arg_type=ArgType.FLOAT, required=True,
            positional=True, position=0, description="Seconds to jump (positive or negative)")
    ]
)
def cmd_jump_relative(cli, seconds: float):
    """Jump by relative time."""
    cli.jump_relative(seconds)


@command(
    name="jump-absolute",
    aliases=["ja"],
    description="Jump to absolute time (ISO format)",
    usage="jump-absolute <timestamp> | ja <timestamp>",
    arguments=[
        arg(name="timestamp", arg_type=ArgType.STRING, required=True,
            positional=True, position=0, description="ISO format timestamp to jump to")
    ]
)
def cmd_jump_absolute(cli, timestamp: str):
    """Jump to absolute time."""
    cli.jump_absolute(timestamp)


@command(
    name="jump-patches",
    aliases=["jp"],
    description="Jump by number of patches",
    usage="jump-patches <num> | jp <num>",
    arguments=[
        arg(name="num", arg_type=ArgType.INT, required=True,
            positional=True, position=0, description="Number of patches to jump (positive or negative)")
    ]
)
def cmd_jump_patches(cli, num: int):
    """Jump by number of patches."""
    cli.jump_patches(num)


@command(
    name="jump-index",
    aliases=["ji"],
    description="Jump to timestamp by index",
    usage="jump-index <index> | ji <index>",
    arguments=[
        arg(name="index", arg_type=ArgType.INT, required=True,
            positional=True, position=0, description="Timestamp index to jump to")
    ]
)
def cmd_jump_index(cli, index: int):
    """Jump to timestamp by index."""
    cli.jump_index(index)


@command(
    name="list-timestamps",
    aliases=["lt"],
    description="List all timestamps with indices",
    usage="list-timestamps [--limit N] [--relative] | lt [--limit N] [--relative]",
    arguments=[
        arg(name="limit", arg_type=ArgType.INT, required=False,
            default=50, description="Maximum number of timestamps to display"),
        arg(name="relative", arg_type=ArgType.BOOL, required=False,
            default=False, description="Show times relative to current position")
    ]
)
def cmd_list_timestamps(cli, limit: int = 50, relative: bool = False):
    """List timestamps."""
    cli.list_timestamps(limit, relative)


# ===== State Viewing Commands =====

@command(
    name="view-state",
    aliases=["vs"],
    description="View game state at path",
    usage="view-state <path> [--depth N] | vs <path> [--depth N]",
    arguments=[
        arg(name="path", arg_type=ArgType.STRING, required=True,
            positional=True, position=0, description="Path to view in game state"),
        arg(name="depth", arg_type=ArgType.INT, required=False,
            default=5, description="Maximum depth to display")
    ]
)
def cmd_view_state(cli, path: str, depth: int = 5):
    """View value at a path in the game state."""
    cli.view_game_object_path(path, depth)


@command(
    name="list-states",
    aliases=["ls"],
    description="List available state categories",
    usage="list-states | ls"
)
def cmd_list_states(cli):
    """List available state categories."""
    cli.list_states()


@command(
    name="search-paths",
    aliases=["sp"],
    description="Search for paths containing a term",
    usage="search-paths <term> | sp <term>",
    arguments=[
        arg(name="term", arg_type=ArgType.STRING, required=True,
            positional=True, position=0, description="Search term to find in paths")
    ]
)
def cmd_search_paths(cli, term: str):
    """Search for paths containing a term."""
    cli.search_paths(term)


# ===== Patch Analysis Commands =====

@command(
    name="list-patches",
    aliases=["lp"],
    description="List all patches with indices",
    usage="list-patches | lp"
)
def cmd_list_patches(cli):
    """List all patches in the replay."""
    cli.list_patches()


@command(
    name="view-patch",
    aliases=["vp"],
    description="View operations in a patch by its index or timestamps",
    usage="view-patch <index> [--limit N] | vp <index> [--limit N] OR view-patch <from_ts> <to_ts> [--limit N]",
    arguments=[
        arg(name="index_or_from", arg_type=ArgType.INT, required=True,
            positional=True, position=0, description="Patch index or from timestamp"),
        arg(name="to_timestamp", arg_type=ArgType.INT, required=False,
            positional=True, position=1, default=None, description="To timestamp (optional)"),
        arg(name="limit", arg_type=ArgType.INT, required=False,
            default=None, description="Maximum number of operations to display")
    ]
)
def cmd_view_patch(cli, index_or_from: int, to_timestamp: int = None, limit: int = None):
    """View operations in a patch."""
    if to_timestamp is not None:
        # Two arguments - treat as timestamps
        cli.view_patch(index_or_from, to_timestamp, limit)
    else:
        # Single argument - treat as index
        cli.view_patch_by_index(index_or_from, limit)


@command(
    name="metadata",
    aliases=["md"],
    description="Display replay metadata",
    usage="metadata | md"
)
def cmd_metadata(cli):
    """Display replay metadata."""
    cli.display_info()


@command(
    name="view-operations-by-path",
    aliases=["vop"],
    description="View operations that match a path prefix",
    usage="view-operations-by-path <path> [--limit N] [--direction forward|backward|both] [--full-width]",
    arguments=[
        arg(name="path_prefix", arg_type=ArgType.STRING, required=True,
            positional=True, position=0, description="Path prefix to filter operations"),
        arg(name="limit", arg_type=ArgType.INT, required=False,
            default=DEFAULT_LIMIT, description="Maximum number of operations to display"),
        arg(name="direction", arg_type=ArgType.STRING, required=False,
            default=DEFAULT_DIRECTION, description="Direction filter: forward, backward, or both"),
        arg(name="full_width", arg_type=ArgType.BOOL, required=False,
            default=False, description="Don't truncate paths and values")
    ]
)
def cmd_view_operations_by_path(cli, path_prefix: str, limit: int = DEFAULT_LIMIT, 
                                  direction: str = DEFAULT_DIRECTION, full_width: bool = False):
    """View all operations that start with a specific path across all patches."""
    cli.view_operations_by_path(path_prefix, limit, direction, full_width)


@command(
    name="operations-overview",
    aliases=["oo"],
    description="Show operations overview grouped by state",
    usage="operations-overview [--direction forward|backward|both] | oo [--direction ...]",
    arguments=[
        arg(name="direction", arg_type=ArgType.STRING, required=False,
            default=DEFAULT_DIRECTION, description="Direction filter: forward, backward, or both")
    ]
)
def cmd_operations_overview(cli, direction: str = DEFAULT_DIRECTION):
    """Show overview of operations grouped by state."""
    cli.operations_overview(direction)


@command(
    name="count-operations",
    aliases=["co"],
    description="Count all operations",
    usage="count-operations | co"
)
def cmd_count_operations(cli):
    """Count total number of operations across all patches."""
    cli.count_operations()


@command(
    name="count-operations-by-path",
    aliases=["cop"],
    description="Count operations that match a path prefix",
    usage="count-operations-by-path <path> [--direction forward|backward|both] | cop <path> [...]",
    arguments=[
        arg(name="path_prefix", arg_type=ArgType.STRING, required=True,
            positional=True, position=0, description="Path prefix to filter operations"),
        arg(name="direction", arg_type=ArgType.STRING, required=False,
            default=DEFAULT_DIRECTION, description="Direction filter: forward, backward, or both")
    ]
)
def cmd_count_operations_by_path(cli, path_prefix: str, direction: str = DEFAULT_DIRECTION):
    """Count operations that start with a specific path."""
    cli.count_operations_by_path(path_prefix, direction)


@command(
    name="check-timestamps",
    description="Check and validate timestamps in the replay",
    usage="check-timestamps"
)
def cmd_check_timestamps(cli):
    """Check timestamps in the replay."""
    cli.check_timestamps()


# ===== Advanced Commands =====

@command(
    name="ritf",
    description="Show ReplayInterface information",
    usage="ritf"
)
def cmd_ritf(cli):
    """Show ReplayInterface info."""
    ritf = cli.get_ritf()
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
    ritf = cli.get_ritf()
    print("\nEntering Python REPL. 'ritf' is available.")
    print("Use Ctrl-D (Unix) or Ctrl-Z (Windows) to exit.\n")
    try:
        import code
        code.interact(local={'ritf': ritf, 'cli': cli})
    except Exception as e:
        print(f"Error: {e}")
