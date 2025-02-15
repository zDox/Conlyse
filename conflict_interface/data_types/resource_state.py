from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from conflict_interface.game_interface import GameInterface
from conflict_interface.utils import GameObject

from dataclasses import dataclass

from .resources import ResourceProfile

@dataclass
class ResourceState(GameObject):
    STATE_ID = 4
    resource_profiles: dict[int, ResourceProfile]

    # Trading, Own Resources
    @classmethod
    def from_dict(cls, obj, game: GameInterface = None):
        resource_profiles = {int(player_id):
                             ResourceProfile.from_dict(resource_profile)
                             for player_id, resource_profile
                             in list(obj["resourceProfs"].items())[1:]}
        instance = cls(**{
            "resource_profiles": resource_profiles,
            })
        instance.game = game
        return instance