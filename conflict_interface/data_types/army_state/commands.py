import math
from copy import copy
from dataclasses import dataclass
from enum import Enum
from typing import Any
from typing import Optional
from typing import Union

from conflict_interface.data_types.custom_types import DateTimeMillisecondsInt
from conflict_interface.data_types.custom_types import DefaultEnumMeta
from conflict_interface.data_types.custom_types import TimeDeltaMillisecondsInt
from conflict_interface.data_types.game_object import GameObject
from conflict_interface.data_types.game_object_binary import SerializationCategory
from conflict_interface.data_types.game_object_binary import binary_serializable
from conflict_interface.data_types.point import Point

@binary_serializable(SerializationCategory.DATACLASS)
@dataclass
class GotoCommand(GameObject):
    """
    Represents a command for an Army to move from one position to another.


    Attributes:
        start_position (Point): The initial position where the movement starts.
        target_position (Point): The destination position where the movement ends.
        speed (float): The speed at which the object moves.
        location_id (int): Optional identifier for the location, defaults to None.
        on_water (bool): Boolean flag indicating if the object moves on water,
            defaults to False.
        start_time (DateTimeMillisecondsInt): Timestamp for when the movement starts,
            defaults to None.
        arrival_time (DateTimeMillisecondsInt): Timestamp for when the movement ends,
            defaults to None.
        speed_factor (float): A multiplier for the speed of the object, defaults to 0.
            This parameter may be recalibrated.
        in_air (bool): Boolean flag indicating if the object moves through the air,
            defaults to False.

    Class Attributes:
        C (str): The command identifier for 'GotoCommand'.
        MAPPING (dict): A dictionary mapping the attribute names to their
            shortened serialized representations.
    """
    C = "gc"


    start_position: Point
    target_position: Point
    speed: float = None

    location_id: int = None
    on_water: bool = None
    start_time: DateTimeMillisecondsInt = None
    arrival_time: DateTimeMillisecondsInt = None
    speed_factor: float = None # TODO Need to check what it should really be
    in_air: bool = None

    MAPPING = {
        "start_time": "st",
        "arrival_time": "at",
        "start_position": "sp",
        "target_position": "tp",
        "speed": "s",
        "on_water": "ow",
        "in_air": "ia",
        "location_id": "l",
        "speed_factor": "sf",
    }

    def action_copy(self) -> "GotoCommand":
        return GotoCommand(
            arrival_time=self.arrival_time,
            speed=self.speed,
            start_position=self.start_position,
            target_position=self.target_position,
            on_water=self.on_water,
            start_time=self.start_time,
            speed_factor=self.speed_factor,
            location_id=self.location_id,
            in_air=self.in_air,
        )

    def get_direction(self) -> float:
        """
        Returns the direction of the movement relative to the current position as radians.
        """
        start_pos = self.start_position
        target_pos = self.target_position
        return math.atan2(-target_pos.x + start_pos.x, target_pos.y - start_pos.y)

@binary_serializable(SerializationCategory.DATACLASS)
@dataclass
class RetreatCommand(GameObject):
    C = "rt"
    MAPPING = {}

    def action_copy(self) -> "RetreatCommand":
        return copy(self)

@binary_serializable(SerializationCategory.DATACLASS)
@dataclass
class AttackCommand(GameObject):
    C = "ac"
    target_unit_id: Optional[int]
    target_position: Optional[Point]
    user_given: bool

    MAPPING = {
        "target_unit_id": "targetUnitID",
        "target_position": "targetPos",
        "user_given": "userGiven",
    }
    def action_copy(self) -> "AttackCommand":
        return copy(self)

@binary_serializable(SerializationCategory.DATACLASS)
@dataclass
class SiegeCommand(GameObject):
    C = "sc"
    MAPPING = {}

@binary_serializable(SerializationCategory.ENUM)
class PatrolType(Enum):
    air_mobile_relocation = "AirMobileRelocation"
    airplane_relocation = "AirplaneRelocation"
    guard = "Guard"
    air_transport = "AirTransport"

@binary_serializable(SerializationCategory.DATACLASS)
@dataclass
class PatrolCommand(GameObject):
    C = "pc"
    target_position: Optional[Point]
    approaching: bool
    patrol_type: PatrolType
    air_field: Optional[str]

    MAPPING = {
        "target_position": "targetPos",
        "approaching": "approaching",
        "patrol_type": "type",
        "air_field": "airField",
    }
    def action_copy(self) -> "PatrolCommand":
        return copy(self)

    def is_relocation(self) -> bool:
        return self.patrol_type != PatrolType.guard

@binary_serializable(SerializationCategory.DATACLASS)
class WaitDirection(Enum, metaclass=DefaultEnumMeta):
    UNKNOWN = -1
    WAITING = 0
    EMBARKING = 1
    DISEMBARKING = 2
    RETURNING = 3
    REFUELING = 4
    EXPLORING = 5
    AIR_EMBARKING = 6
    AIR_DISEMBARKING = 7
    DISBANDING = 8

@binary_serializable(SerializationCategory.DATACLASS)
@dataclass
class WaitCommand(GameObject):
    """
    Attributes:
        wait_time (TimeDela): The amount of time the unit will wait before executing the next command.
        cancelable (bool): Boolean flag indicating if the command can be canceled.
        direction (int): Unknown
        location_id (int): Identifier for the province the unit is waiting in. Most of the time its just 0.
        execute_time (DateTimeMillisecondsInt): Timestamp for when wait command starts.
    """
    C = "wc"
    wait_time: TimeDeltaMillisecondsInt # timedelta seconds
    cancelable: bool
    direction: WaitDirection
    location_id: int
    execute_time: DateTimeMillisecondsInt

    MAPPING = {
        "wait_time": "waitSeconds",
        "cancelable": "cancelable",
        "direction": "direction",
        "location_id": "locationID",
        "execute_time": "execTime",
    }

    def action_copy(self) -> "WaitCommand":
        return copy(self)

    def is_waiting(self) -> bool:
        """
        Check if the wait command is in a waiting state.

        Returns:
            bool: True if waiting, False otherwise.
        """
        return self.direction == WaitDirection.WAITING

    def is_embarking(self) -> bool:
        """
        Check if the wait command is in an embarking state.

        Returns:
            bool: True if embarking, False otherwise.
        """
        return self.direction == WaitDirection.EMBARKING

    def is_disembarking(self) -> bool:
        """
        Check if the wait command is in a disembarking state.

        Returns:
            bool: True if disembarking, False otherwise.
        """
        return self.direction == WaitDirection.DISEMBARKING

    def is_returning(self) -> bool:
        """
        Check if the wait command is in a returning state.

        Returns:
            bool: True if returning, False otherwise.
        """
        return self.direction == WaitDirection.RETURNING

    def is_refueling(self) -> bool:
        """
        Check if the wait command is in a refueling state.

        Returns:
            bool: True if refueling, False otherwise.
        """
        return self.direction == WaitDirection.REFUELING

    def is_exploring(self) -> bool:
        """
        Check if the wait command is in an exploring state.

        Returns:
            bool: True if exploring, False otherwise.
        """
        return self.direction == WaitDirection.EXPLORING

    def is_air_embarking(self) -> bool:
        """
        Check if the wait command is in an air embarking state.

        Returns:
            bool: True if air embarking, False otherwise.
        """
        return self.direction == WaitDirection.AIR_EMBARKING

    def is_air_disembarking(self) -> bool:
        """
        Check if the wait command is in an air disembarking state.

        Returns:
            bool: True if air disembarking, False otherwise.
        """
        return self.direction == WaitDirection.AIR_DISEMBARKING

    def is_disbanding(self) -> bool:
        """
        Check if the wait command is in a disbanding state.

        Returns:
            bool: True if disbanding, False otherwise.
        """
        return self.direction == WaitDirection.DISBANDING

@binary_serializable(SerializationCategory.DATACLASS)
@dataclass
class SplitArmyCommand(GameObject):
    C = "sac"
    splitted_army: Any
    MAPPING = {
        "splitted_army": "splittedArmy",
    }
    def action_copy(self) -> "SplitArmyCommand":
        return copy(self)

@binary_serializable(SerializationCategory.DATACLASS)
@dataclass
class FireMissileCommand(GameObject):
    C = "fm"
    MAPPING = {}

    def action_copy(self) -> "FireMissileCommand":
        return copy(self)

COMMAND_TYPES = [GotoCommand, RetreatCommand, AttackCommand, SiegeCommand,
                 PatrolCommand, WaitCommand, SplitArmyCommand,
                 FireMissileCommand]

Command: Union = Union[GotoCommand, RetreatCommand, AttackCommand, SiegeCommand,
                  PatrolCommand, WaitCommand, SplitArmyCommand,
                  FireMissileCommand]