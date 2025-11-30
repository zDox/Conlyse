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
from datetime import datetime, timedelta

from tools.replay_debug.command_registry import command, arg, ArgType


@command(
    name="info",
    description="Display current replay position and metadata",
    usage="info"
)
def cmd_info(cli):
    """Display current replay position and metadata."""
    if not cli.ritf:
        print("Error: Replay not opened.")
        return

    idx, current, start, end = cli.navigator.get_current_position_info()

    print("\nReplay Information")
    print("=" * 80)
    print(f"File:        {cli.filename}")
    print(f"Game ID:     {cli.ritf.game_id}")
    print(f"Game Speed: {cli.ritf.speed_modifier}")
    print(f"Player ID:   {cli.ritf.player_id}")
    print(f"\nStart Time:  {start.isoformat()}")
    print(f"End Time:    {end.isoformat()}")
    print(f"Duration:    {(end - start).total_seconds():.2f} seconds")
    print(f"\nCurrent Position:")
    print(f"  Time:      {current.isoformat()}")
    print(f"  Index:     {idx}")
    print(f"  Progress:  {((current - start).total_seconds() / (end - start).total_seconds() * 100):.1f}%")

    # Show timestamp stats
    timestamps = cli.ritf.get_timestamps()
    print(f"\nTotal Timestamps: {len(timestamps)}")


@command(
    name="jump-relative",
    aliases=["jr"],
    description="Jump by relative time (accepts suffixes s, h, d, w — e.g. 1s, 1h, 1d, 1w)",
    usage="jump-relative <timedelta> | jr <timedelta> (e.g. 1s, 1h, 1d, 1w)",
    arguments=[
        arg(name="time_delta", arg_type=ArgType.TIMEDELTA, required=True,
            positional=True, position=0, description="Timedelta string, e.g. 1s, 1h, 1d, 1w")
    ]
)
def cmd_jump_relative(cli, time_delta: timedelta):
    """Jump by relative time."""
    if not cli.navigator:
        print("Error: Replay not opened.")
        return

    if cli.navigator.jump_by_relative_time(time_delta.total_seconds()):
        print(f"Jumped to: {cli.ritf.current_time.isoformat()}")
    else:
        print("Failed to jump.")


@command(
    name="jump-absolute",
    aliases=["ja"],
    description="Jump to absolute time",
    usage="jump-absolute <timestamp> | ja <timestamp>",
    arguments=[
        arg(name="timestamp", arg_type=ArgType.DATETIME, required=True,
            positional=True, position=0, description="timestamp to jump to")
    ]
)
def cmd_jump_absolute(cli, timestamp: datetime):
    """Jump to absolute time."""
    if not cli.navigator:
        print("Error: Replay not opened.")
        return
    try:
        if cli.navigator.jump_to_absolute_time(timestamp):
            print(f"Jumped to: {cli.ritf.current_time.isoformat()}")
        else:
            print("Failed to jump.")
    except Exception as e:
        print(f"Error parsing timestamp: {e}")


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
    if not cli.navigator:
        print("Error: Replay not opened.")
        return

    if cli.navigator.jump_by_patches(num):
        print(f"Jumped to: {cli.ritf.current_time.isoformat()}")
    else:
        print("Failed to jump.")


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
    if not cli.navigator:
        print("Error: Replay not opened.")
        return

    if cli.navigator.jump_to_timestamp_index(index):
        print(f"Jumped to: {cli.ritf.current_time.isoformat()}")
    else:
        print("Failed to jump.")


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
    """List timestamps.
    Args:
        limit: Maximum number of timestamps to display
        relative: If True, show times relative to current position
    """
    if not cli.navigator:
        print("Error: Replay not opened.")
        return

    cli.navigator.list_timestamps(limit, relative)
