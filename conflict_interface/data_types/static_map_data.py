from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from conflict_interface.game_interface import GameInterface
from conflict_interface.utils.game_object import GameObject

from dataclasses import dataclass

from conflict_interface.data_types.province.province import StaticProvince


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
