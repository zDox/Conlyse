

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Union, Any
from enum import Enum

from conflict_interface.data_types.game_object import GameObject
from conflict_interface.data_types.point import Point


@dataclass
class GotoCommand(GameObject):
    """
    Command that tells a army to move
    """
    C = "ultshared.UltGotoCommand"
    start_time: datetime
    arrival_time: datetime

    start_position: Point
    target_position: Point
    speed: float

    on_water: bool
    in_air: bool
    location_id: int
    speed_factor: float

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
    pass


@dataclass
class AttackCommand(GameObject):
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
    pass


class PatrolType(Enum):
    air_mobile_relocation = "AirMobileRelocation"
    guard = "Guard"


@dataclass
class PatrolCommand(GameObject):
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
    splitted_army: Any
    MAPPING = {
        "splitted_army": "splittedArmy",
    }


@dataclass
class FireMissileCommand(GameObject):
    pass


COMMAND_TYPES = [GotoCommand, RetreatCommand, AttackCommand, SiegeCommand,
                 PatrolCommand, WaitCommand, SplitArmyCommand,
                 FireMissileCommand]

Command: Union = [GotoCommand, RetreatCommand, AttackCommand, SiegeCommand,
                  PatrolCommand, WaitCommand, SplitArmyCommand,
                  FireMissileCommand]

COMMAND_IDENTIFIERS = {
    "gc": GotoCommand,
    "rt": RetreatCommand,
    "ac": AttackCommand,
    "sc": SiegeCommand,
    "pc": PatrolCommand,
    "wc": WaitCommand,
    "sac": SplitArmyCommand,
    "fm": FireMissileCommand,
}


def parse_command(obj):
    print(obj)
    return COMMAND_IDENTIFIERS[obj.get("@c")].from_dict(obj)
