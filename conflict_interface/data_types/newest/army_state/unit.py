import math
from dataclasses import dataclass

from conflict_interface.game_object.game_object import GameObject
from conflict_interface.game_object.game_object_binary import SerializationCategory
from conflict_interface.game_object.decorators import conflict_serializable
from conflict_interface.data_types.mod_state.mod_state_enums import UnitFeature
from conflict_interface.data_types.mod_state.unit_type import UnitType

from conflict_interface.data_types.version import VERSION
@conflict_serializable(SerializationCategory.DATACLASS, version = VERSION)
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
        camouflage_replacement_unit (bool): Indicates if the unit is a camouflage replacement.
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
    camouflage_replacement_unit: bool = False
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
        "camouflage_replacement_unit": "cru",
        "on_sea": "os",
        "at_airfield": "aa",
        "hit_points": "hp",
        "max_hit_points": "mhp",
    }

    def action_copy(self) -> "Unit":
        return Unit(
            id = self.id,
            unit_type_id = self.unit_type_id,
            health = self.health,
            size = self.size,
            kills = self.kills,
            at_airfield = self.at_airfield,
            on_sea=self.on_sea
        )

    def get_unit_type(self) -> UnitType:
        return self.game.get_unit_type(self.unit_type_id)

    def has_feature(self, feature: UnitFeature) -> bool:
        unit_type = self.game.get_unit_type(self.unit_type_id)
        return unit_type.has_feature(feature)

    def is_ship(self) -> bool:
        return self.has_feature(UnitFeature.SHIP)

    @staticmethod
    def get_image_index(angle):
        army_angles = 12
        step = 2 * math.pi / army_angles
        index = (angle + math.pi + step / 2) / step
        return math.floor(index) % army_angles

    def get_image(self, unit_type: UnitType,status: str, is_moving: bool = False, angle_index: int = None):
        if angle_index is None:
            angle_index = unit_type.get_default_angle_index()
        return unit_type.get_icon_key_ww2(
            variant=status,
            category=2,
            angle=angle_index,
            is_moving=is_moving,
            faction=self.game.get_faction(), # TODO Take the faction of the actual owner of the Unit
        ) + ".png"