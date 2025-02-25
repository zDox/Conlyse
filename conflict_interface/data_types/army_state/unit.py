

from dataclasses import dataclass
from enum import Enum

from conflict_interface.data_types.game_object import GameObject


class MissileType(Enum):
    BALLISTIC = 1
    CRUISE = 2


@dataclass
class Unit(GameObject):
    C = "ultshared.warfare.UltUnit"
    id: int
    unit_type_id: int
    health: float
    size: int
    kills: int
    camoflage_replacement_unit: int
    on_sea: bool
    at_airfield: bool
    hit_points: float
    max_hit_points: int

    MAPPING = {
        "id": "id",
        "unit_type_id": "t",
        "health": "h",
        "size": "s",
        "kills": "k",
        "camoflage_replacement_unit": "cru",
        "on_sea": "os",
        "at_airfield": "aa",
        "hit_points": "hp",
        "max_hit_points": "mhp",
    }

    def is_airplane(self):
        return False

    def set_size(self, size):
        self.size = int(size)

    def get_size(self):
        return self.size

    def get_health(self):
        return self.health

    def get_morale_percent(self):
        return round(100 * self.health)

    def get_kills(self):
        return self.kills

    def get_air_view_width(self):
        return 0

    def get_patrol_radius(self):
        return 0

    def get_unit_type_id(self):
        return self.unit_type_id

    def get_production_time(self):
        return 0

    def is_on_sea(self):
        return self.onSea

    def is_at_airfield(self):
        return self.atAirfield

    def is_elite(self):
        return False

    def is_camouflage_replacement_unit(self):
        return self.camouflageReplacementUnit

    def calculate_terrain(self, is_on_sea, is_rail, is_at_airfield,
                          is_airplane=None):
        raise NotImplementedError()

    def get_terrain_class(self):
        return self.army.get_terrain_class() \
                if self.army else \
                self.calculate_terrain(self.is_on_sea(), False,
                                       self.is_at_airfield())

    def is_carriable(self):
        return False

    def can_fly(self):
        return self.is_airplane()

    def can_use_airfields(self):
        return self.is_airplane() or self.is_air_transportable()

    def is_air_relocatable(self):
        return self.can_use_airfields() and not self.is_rocket()

    def get_favourite_terrain_class(self):
        raise NotImplementedError()

    def is_air_transportable(self):
        return False

    def is_token_consumer(self):
        return False

    def is_disbandable(self):
        return False

    def get_disband_config(self):
        return None

    def set_army(self, army):
        self.army = army

    def get_army(self):
        return self.army

    def get_slot_capacity(self, b):
        return 0

    def get_carriable_type(self):
        return 0


