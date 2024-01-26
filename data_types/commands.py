
from data_types.utils import JsonMappedClass, MappedValue, Position, \
        unixtimestamp_to_datetime


from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Union, Any
from enum import Enum


@dataclass
class GotoCommand(JsonMappedClass):
    start_time: datetime
    arrival_time: datetime

    start_position: Position
    target_position: Position
    speed: float

    on_water: bool
    in_air: bool
    location_id: int
    speed_factor: float

    mapping = {
        "start_time": MappedValue("st", unixtimestamp_to_datetime),
        "arrival_time": MappedValue("at", unixtimestamp_to_datetime),
        "start_position": "sp",
        "target_position": "tp",
        "speed": "s",
        "on_water": "ow",
        "in_air": "ia",
        "location_id": "l",
        "speed_factor": "sf",
    }


@dataclass
class RetreatCommand(JsonMappedClass):
    pass


@dataclass
class AttackCommand(JsonMappedClass):
    target_unit_id: int
    target_position: Position
    user_given: bool

    mapping = {
        "target_unit_id": "targetUnitID",
        "target_pos": "targetPos",
        "user_given": "userGiven",
    }


@dataclass
class SiegeCommand(JsonMappedClass):
    pass


class PatrolType(Enum):
    air_mobile_relocation = "AirMobileRelocation"
    guard = "Guard"


@dataclass
class PatrolCommand(JsonMappedClass):
    target_position: Position
    approaching: bool
    patrol_type: PatrolType

    mapping = {
        "target_position": "targetPos",
        "approaching": "approaching",
        "patrol_type": "type",
    }


@dataclass
class WaitCommand(JsonMappedClass):
    wait_time: timedelta
    cancelable: bool
    direction: int
    location_id: int
    execute_time: int

    mapping = {
        "wait_time": "waitSeconds",
        "cancelable": "cancelable",
        "direction": "direction",
        "location_id": "locationID",
        "execute_time": "execTime",
    }


# to circumvent circular imports
def parse_army(obj):
    from data_types.army import Army
    return Army.from_dict(obj)


@dataclass
class SplitArmyCommand(JsonMappedClass):
    splitted_army: Any
    mapping = {
        "splitted_army": MappedValue("splittedArmy", parse_army),
    }


@dataclass
class FireMissileCommand(JsonMappedClass):
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
