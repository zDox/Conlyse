"""
Central place for datatype version support.

Use get_supported_datatype_versions() to check which game/client datatype versions
this library can parse and serialize. Use LATEST_VERSION for the newest supported
version (e.g. for new games or API clients).
"""
from __future__ import annotations

# Import so that JsonParser.GAME_STATES is populated (via data_types registration)
from conflict_interface.game_object.game_object_parse_json import JsonParser
from conflict_interface.data_types.newest.version import VERSION as _LATEST_VERSION

# Re-export as the canonical name for "latest supported datatype version"
LATEST_VERSION: int = _LATEST_VERSION


def get_supported_datatype_versions() -> set[int]:
    """
    Return the set of datatype versions this library supports (for replays and parsing).

    These are the client/game versions for which GameState (and related types) are
    registered. ReplayBuilder and ReplayInterface use these versions.
    """
    return set(JsonParser.GAME_STATES.keys())
