from dataclasses import dataclass
from typing import Optional

from conflict_interface.data_types.game_object_binary import SerializationCategory
from conflict_interface.data_types.game_object_binary import binary_serializable
from conflict_interface.data_types.map_state.map import Map
from conflict_interface.data_types.custom_types import HashMap
from conflict_interface.data_types.game_object import GameObject
from conflict_interface.data_types.map_state.province_property import ProvinceProperty
from conflict_interface.data_types.state import State
from conflict_interface.data_types.state import state_update
from conflict_interface.replay.replay_patch import BidirectionalReplayPatch
from conflict_interface.replay.replay_patch import PathNode


@binary_serializable(SerializationCategory.DATACLASS)
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
    properties: Optional[HashMap[int, ProvinceProperty]]

    change_set: bool
    MAPPING = {
        "map": "map",
        "properties": "properties",
        "change_set": "changeSet"
    }

    def update(self, other: GameObject, path: list[PathNode] = None, rp: BidirectionalReplayPatch = None):
        if not isinstance(other, MapState):
            raise ValueError("UPDATE ERROR: Cannot update MapState with object of type: " + str(type(other)))
        state_update(self, other, path=path, rp=rp)

        if other.map is not None:
            for province in other.map.locations:
                if province.id not in self.map.provinces:
                    if rp:
                        rp.add(path + ["map", "locations", -1], self.map.provinces.get(province.id), province)
                    self.map.locations.append(province)
                else:
                    self.map.provinces[province.id].update(
                        province,
                        path + ["map", "locations", self.map.province_id_to_index(province.id)],
                        rp
                    )
            self.map.clear_cache()

        if other.properties is not None:
            if self.properties is None:
                self.properties = other.properties
                if rp:
                    rp.replace(path + ["properties"], self.properties, other.properties)
                return
            for province_id, prop in other.properties.items():
                if rp:
                    rp.replace(path + ["properties", province_id], self.properties.get(province_id), prop)
                self.properties[province_id] = prop
                self.map.provinces[province_id]._properties = prop
