from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from conflict_interface.game_interface import GameInterface
from conflict_interface.utils import GameObject, HashMap

from dataclasses import dataclass

from .resource_profile import ResourceProfile

@dataclass
class ResourceState(GameObject):
    STATE_ID = 4
    resource_profiles: HashMap[int, ResourceProfile]

    MAPPING = {
        "resource_profiles": "resourceProfs"
    }