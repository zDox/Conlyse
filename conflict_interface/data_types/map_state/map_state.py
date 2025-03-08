from dataclasses import dataclass
from typing import override

from conflict_interface.data_types.map_state.map import Map
from conflict_interface.data_types.custom_types import HashMap
from conflict_interface.data_types.game_object import GameObject
from conflict_interface.data_types.map_state.province_property import ProvinceProperty
from conflict_interface.data_types.state import State


@dataclass
class MapState(State):
    """
    Represents the state of a map within a game.

    This class is used to store and manage the state of the map and player-owned
    provinces within the context of the game.
    """
    C = "ultshared.UltMapState"
    STATE_TYPE = 3
    map: Map
    # Provinces which are owned by the current player
    properties: HashMap[int, ProvinceProperty]

    change_set: bool

    MAPPING = {
        "map": "map",
        "properties": "properties",
        "change_set": "changeSet"
    }

    @override
    def update(self, other: GameObject):
        if not isinstance(other, MapState):
            raise ValueError("UPDATE ERROR: Cannot update MapState with object of type: " + str(type(other)))

        if other.map is not None:
            self.map.update(other.map)

        if other.properties is not None:
            for province_id, prop in other.properties.items():
                if province_id in self.properties:
                    if self.properties[province_id] is None:
                        self.properties[province_id] = prop
                    self.properties[province_id].update(prop)
                else:
                    self.properties[province_id] = prop

