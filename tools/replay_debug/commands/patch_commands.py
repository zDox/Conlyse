"""
Patch analysis commands for the Replay Debug CLI Tool.

This module defines commands for analyzing patches:
- list-patches (lp): List all patches with indices
- view-patch (vp): View operations in a patch
- metadata (md): Display replay metadata
- view-operations-by-path (vop): View operations that match a path prefix
- operations-overview (oo): Show operations overview grouped by state
- count-operations (co): Count all operations
- count-operations-by-path (cop): Count operations that match a path prefix
- check-timestamps: Check and validate timestamps
"""
from tools.replay_debug.command_registry import command, arg, ArgType
from tools.replay_debug.constants import DEFAULT_LIMIT, DEFAULT_DIRECTION


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
