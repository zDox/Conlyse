

from dataclasses import dataclass
from enum import Enum

from conflict_interface.data_types.game_object import GameObject


class MissileType(Enum):
    BALLISTIC = 1
    CRUISE = 2


@dataclass
class Unit(GameObject):
    """
    Represents a unit in the game with associated properties and behaviors.

    Attributes:
        C (str): A constant string identifier for the class.
        id (int): Unique identifier for the unit.
        unit_type_id (int): Identifier for the type of unit.
        health (float): The current health of the unit in percent.
        size (int): Represents the number of units this unit contains.
        kills (int): The number of kills attributed to this unit.
        camoflage_replacement_unit (bool): Indicates if the unit is a camouflage replacement.
        on_sea (bool): Denotes whether the unit operates on the sea.
        at_airfield (bool): Indicates if the unit is currently stationed at an airfield.
        hit_points (float): Represents the current hit points of the unit.
        max_hit_points (int): The maximum hit points the unit can achieve.

        MAPPING (dict): A dictionary that maps internal attribute names to their
            corresponding representations in external systems.

    Methods:
        is_airplane: Checks if the unit represents an airplane.
        set_size: Sets the size of the unit.
        get_size: Retrieves the size of the unit.
        get_health: Retrieves the health value of the unit.
        get_morale_percent: Calculates and returns the morale percentage based on health.
        get_kills: Retrieves the number of kills attributed to the unit.
        get_air_view_width: Returns the air view width for the unit (default 0).
        get_patrol_radius: Returns the patrol radius for the unit (default 0).
        get_unit_type_id: Retrieves the unit type identifier.
        get_production_time: Returns the production time of the unit (default 0).
        is_on_sea: Checks if the unit operates on the sea.
        is_at_airfield: Checks if the unit is stationed at an airfield.
        is_elite: Checks if the unit is classified as elite.
        is_camouflage_replacement_unit: Checks if the unit is a camouflage replacement.
        calculate_terrain: Method to be implemented to calculate terrain effects.
        get_terrain_class: Retrieves the terrain class for the unit.
        is_carriable: Checks if the unit can be carried.
        can_fly: Checks if the unit has flying capabilities.
        can_use_airfields: Determines if the unit can use airfields.
        is_air_relocatable: Checks if the unit is air-relocatable.
        get_favourite_terrain_class: Method to be implemented to retrieve preferred terrain.
        is_air_transportable: Checks if the unit can be transported by air.
        is_token_consumer: Checks if the unit consumes tokens.
        is_disbandable: Checks if the unit can be disbanded.
        get_disband_config: Retrieves the disband configuration if available.
        set_army: Sets the associated army for the unit.
        get_army: Retrieves the associated army of the unit.
        get_slot_capacity: Returns the slot capacity of the unit (default 0).
        get_carriable_type: Retrieves the carriable type of the unit (default 0).
    """
    C = "u"
    id: int
    unit_type_id: int
    health: float = 0
    size: int = 0
    kills: int = 0
    camoflage_replacement_unit: bool = False
    on_sea: bool = False
    at_airfield: bool = False
    hit_points: float = 0
    max_hit_points: int = 0

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


