

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Union, Any, Optional
from enum import Enum

from conflict_interface.data_types.game_object import GameObject
from conflict_interface.data_types.point import Point


@dataclass
class GotoCommand(GameObject):
    """
    Command that tells a army to move
    """
    C = "gc"


    start_position: Point
    target_position: Point
    speed: float

    location_id: int = None
    on_water: bool = False
    start_time: datetime = None
    arrival_time: datetime = None
    speed_factor: float = 0 # TODO Need to check what it should really be
    in_air: bool = False

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
    target_unit_id: int
    target_position: Point
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
    guard = "Guard"


@dataclass
class PatrolCommand(GameObject):
    C = "pc"
    target_position: Point
    approaching: bool
    patrol_type: PatrolType

    MAPPING = {
        "target_position": "targetPos",
        "approaching": "approaching",
        "patrol_type": "type",
    }


@dataclass
class WaitCommand(GameObject):
    C = "wc"
    wait_time: timedelta
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