from __future__ import annotations
from typing import TYPE_CHECKING


from dataclasses import dataclass

from .resource_profile import ResourceProfile
from ..custom_types import HashMap
from ..game_object import GameObject


@dataclass
class ResourceState(GameObject):
    C = "ultshared.UltResourceState"
    STATE_ID = 4
    resource_profiles: HashMap[int, ResourceProfile]

    MAPPING = {
        "resource_profiles": "resourceProfs"
    }