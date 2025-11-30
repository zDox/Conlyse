"""
Navigation commands for the Replay Debug CLI Tool.

This module defines commands for navigating through the replay timeline:
- info: Display current replay position and metadata
- jump-relative (jr): Jump by relative time
- jump-absolute (ja): Jump to absolute time
- jump-patches (jp): Jump by number of patches
- jump-index (ji): Jump to timestamp by index
- list-timestamps (lt): List all timestamps with indices
"""
from tools.replay_debug.command_registry import command, arg, ArgType


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
