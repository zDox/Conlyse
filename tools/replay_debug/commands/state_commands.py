"""
State viewing commands for the Replay Debug CLI Tool.

This module defines commands for viewing and searching game state:
- view-state (vs): View game state at path
- list-states (ls): List available state categories
- search-paths (sp): Search for paths containing a term
"""
from tools.replay_debug.command_registry import command, arg, ArgType


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
    if not cli.game_object_viewer:
        print("Error: Replay not opened.")
        return

    cli.game_object_viewer.view_path(path, depth)


@command(
    name="list-states",
    aliases=["ls"],
    description="List available state categories",
    usage="list-states | ls"
)
def cmd_list_states(cli):
    """List available state categories."""
    if not cli.game_object_viewer:
        print("Error: Replay not opened.")
        return

    cli.game_object_viewer.list_available_states()


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

    if not cli.game_object_viewer:
        print("Error: Replay not opened.")
        return

    cli.game_object_viewer.search_path(term)