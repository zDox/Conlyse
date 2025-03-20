from dataclasses import dataclass
from typing import Optional
from typing import override

from conflict_interface.data_types.map_state.map import Map
from conflict_interface.data_types.custom_types import HashMap
from conflict_interface.data_types.game_object import GameObject
from conflict_interface.data_types.map_state.province_property import ProvinceProperty
from conflict_interface.data_types.state import State
from conflict_interface.replay.replay_patch import PathNode
from conflict_interface.replay.replay_patch import ReplayPatch


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

    def update(self, other: GameObject, path: list[PathNode] = None, rp: ReplayPatch = None):
        if not isinstance(other, MapState):
            raise ValueError("UPDATE ERROR: Cannot update MapState with object of type: " + str(type(other)))
        super().update(other, path=path, rp=rp)

        if other.map is not None:
            for province in other.map.locations:
                if province.id not in self.map.provinces:
                    self.map.locations.append(province)
                    rp.add_op(path + ["map", "locations", -1], province)
                else:
                    self.map.provinces[province.id].update(
                        province,
                        path + ["map", "locations", self.map.province_id_to_index(province.id)],
                        rp
                    )
            self.map.clear_cache()

        if other.properties is not None:
            if any(province_id not in self.properties for province_id  in other.properties.keys()):
                self.properties = other.properties
                rp.replace_op(path + ["properties"], other.properties)
                return
            for province_id, prop in other.properties.items():
                self.properties[province_id] = prop
                self.map.provinces[province_id]._properties = prop
                rp.replace_op(path + ["properties", province_id], prop)