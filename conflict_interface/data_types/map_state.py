from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from conflict_interface.game_interface import GameInterface
from conflict_interface.utils import GameObject

from dataclasses import dataclass
from pprint import pprint

from .province import Province, ProvinceProperty
from .static_map_data import StaticMapData


@dataclass
class MapState(GameObject):
    STATE_ID = 3
    provinces: dict[int, Province]
    # Provinces which are owned by the current player
    province_properties: dict[int, ProvinceProperty]

    @classmethod
    def from_dict(cls, obj, game: GameInterface = None):
        provinces = {province["id"]: Province.from_dict(province)
                     for province in obj["map"]["locations"][1]}

        province_properties = {int(province_id): ProvinceProperty.
                               from_dict({**province_property,
                                          "id": int(province_id)})
                               for province_id, province_property
                               in list(obj["properties"].items())[1:]}

        for province_property in province_properties.values():
            provinces[province_property.id].properties = province_property

        instance = cls(**{
            "provinces": provinces,
            "province_properties": province_properties,
        })
        instance.game = game
        return instance

    def update(self, new_state):
        for province in new_state.provinces:
            self.provinces[province.province_id].update(province)

    def set_static_map_data(self, static_map_data: StaticMapData):
        for province in static_map_data.provinces:
            self.provinces[province.id].set_static_province(province)
