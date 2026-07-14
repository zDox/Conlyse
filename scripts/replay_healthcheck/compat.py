"""Datatype-version compatibility pre-check.

Lets the health check classify a replay as version-incompatible *before*
attempting a full parse, instead of hitting a raw KeyError mid-parse
(GameObjectSerializer._from_raw_registered raises "Unknown type_id ..." when
a replay was recorded with a datatype version this build doesn't have
registered).
"""

from conflict_interface.versions import get_supported_datatype_versions


def unsupported_versions(required: set[int]) -> set[int]:
    """Return the subset of `required` datatype versions this build cannot parse."""
    return required - get_supported_datatype_versions()
