from __future__ import annotations
from typing import TYPE_CHECKING

from dataclasses import dataclass

from conflict_interface.data_types.custom_types import ArrayList
from conflict_interface.data_types.map_state.static_province import StaticProvince

if TYPE_CHECKING:
    from conflict_interface.game_interface import GameInterface
from conflict_interface.data_types.game_object import GameObject


@dataclass
class StaticMapData(GameObject):
    locations: ArrayList[StaticProvince]

    MAPPING = {
        "locations": "locations"
    }
