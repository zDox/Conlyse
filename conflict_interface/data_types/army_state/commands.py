

from dataclasses import dataclass
from enum import Enum
from typing import Any
from typing import Optional
from typing import Union

from conflict_interface.data_types.custom_types import DateTimeMillisecondsInt
from conflict_interface.data_types.custom_types import TimeDeltaMillisecondsInt
from conflict_interface.data_types.custom_types import TimeDeltaSecondsInt
from conflict_interface.data_types.game_object import GameObject
from conflict_interface.data_types.point import Point


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


@dataclass
class RetreatCommand(GameObject):
    C = "rt"
    MAPPING = {}


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


@dataclass
class SiegeCommand(GameObject):
    C = "sc"
    MAPPING = {}


class PatrolType(Enum):
    air_mobile_relocation = "AirMobileRelocation"
    airplane_relocation = "AirplaneRelocation"
    guard = "Guard"


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
    direction: int
    location_id: int
    execute_time: int

    MAPPING = {
        "wait_time": "waitSeconds",
        "cancelable": "cancelable",
        "direction": "direction",
        "location_id": "locationID",
        "execute_time": "execTime",
    }


@dataclass
class SplitArmyCommand(GameObject):
    C = "sac"
    splitted_army: Any
    MAPPING = {
        "splitted_army": "splittedArmy",
    }


@dataclass
class FireMissileCommand(GameObject):
    C = "fm"
    MAPPING = {}

COMMAND_TYPES = [GotoCommand, RetreatCommand, AttackCommand, SiegeCommand,
                 PatrolCommand, WaitCommand, SplitArmyCommand,
                 FireMissileCommand]

Command: Union = Union[GotoCommand, RetreatCommand, AttackCommand, SiegeCommand,
                  PatrolCommand, WaitCommand, SplitArmyCommand,
                  FireMissileCommand]