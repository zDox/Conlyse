from __future__ import annotations
from typing import TYPE_CHECKING

from dataclasses import dataclass

from conflict_interface.data_types.map_state.province import StaticProvince

if TYPE_CHECKING:
    from conflict_interface.game_interface import GameInterface
from conflict_interface.data_types.game_object import GameObject


@dataclass
class StaticMapData(GameObject):
    provinces: list[StaticProvince]

    @classmethod
    def from_dict(cls, obj, game: GameInterface = None):
        provinces = []
        for province in obj["locations"][1]:
            provinces.append(StaticProvince.from_dict(province))

        instance = cls(**{
            "provinces": provinces,
            })
        instance.game = game
        return instance
