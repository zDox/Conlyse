from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from data_types.utils import JsonMappedClass, MappedValue, Position, \
        DefaultEnumMeta, unixtimestamp_to_datetime
from data_types.warfare_unit import Unit
from data_types.province import TerrainType
from data_types.features import CarrierFeature, MissileCarrierFeature, \
        RadarSignatureFeature, TokenFeature
from data_types.commands import Command, parse_command

ARMY_CLOSE_COMBAT_RANGE = 5


def parse_units(value: list):
    if value is None:
        return []

    return [Unit.from_dict(unit) for unit in value[1]]


def parse_commands(value: list):
    if value is None:
        return []

    return [parse_command(command) for command in value[1]]


@dataclass
class Battle(JsonMappedClass):
    attacker_ids: list[int]

    @classmethod
    def from_dict(cls, obj):
        return cls(**{
            "attacker_ids": [attacker_id for attacker_id in obj["a"]],
            })


class FightStatus(Enum, metaclass=DefaultEnumMeta):
    IDLE = 0
    FIGHTING = 1
    BOMBARDING = 2
    PATROLING = 3
    APPROACH_PATROL = 4
    SIEGING = 5
    ANTI_AIR = 6
    BOMBING = 7


class Aggressiveness(Enum, metaclass=DefaultEnumMeta):
    DEFAULT = 0
    HOLD_FIRE = 1
    RETURN_FIRE = 2
    NORMAL = 3
    AGGRESIVE = 4


class ForcedMarch(Enum, metaclass=DefaultEnumMeta):
    DEACTIVE = 0
    ACTIVE = 1
    PREMIUM = 2


def parse_air_field(obj):
    if obj is None:
        return None
    elif "x" in obj:
        return Position.from_dict(obj)
    elif obj.get("@c") == "ultshared.warfare.UltTemporaryAirfield":
        return Position.from_dict(obj["airfieldPosition"])
    else:
        return int(obj[1:])


@dataclass
class AirParameters(JsonMappedClass):
    last_air_action_time: datetime
    last_air_position: Position
    launch_target: Position
    max_flight_time: datetime
    air_field: Position | int  # Can be either a province_id or a Position

    mapping = {
        "last_air_action_time": MappedValue("lastAirActionTime",
                                            unixtimestamp_to_datetime),
        "last_air_position": "lastAirPosition",
        "launch_target": "launchTarget",
        "max_flight_time": MappedValue("maxFlightTime",
                                       unixtimestamp_to_datetime),
        "air_field": MappedValue("airField", parse_air_field),
    }


@dataclass
class AntiAirParameters(JsonMappedClass):
    next_anti_air_attack: datetime
    last_anti_air_attack: datetime
    last_anti_air_attack_distance: float

    mapping = {
        "next_anti_air_attack": MappedValue("naa", unixtimestamp_to_datetime),
        "last_anti_air_attack": MappedValue("laa", unixtimestamp_to_datetime),
        "last_anti_air_attack_distance": "laadist",
    }


@dataclass
class Army(JsonMappedClass):
    id: int = None
    size: int = 1
    health: float = 1.0
    kills: int = 0
    owner_id: int = None
    army_number: int = None
    location_id: int = None
    position: Position = None
    last_direction: Position = None
    on_sea: bool = False
    at_airfield: bool = False
    units: list[Unit] = None

    commands: list[Command] = None
    fight_status: FightStatus = FightStatus.IDLE
    battle: Battle = None
    attack_unit_id: int = None
    attack_position: Position = None
    next_attack_time: datetime = None
    estimated_arrival_time: datetime = None

    # I do not now any unit which needs rail but whatever
    needs_rail: bool = False
    needs_water: bool = False
    has_stealth: bool = False
    airplane: bool = False

    pre_fight_size: int = None
    pre_fight_type: int = None

    range: int = ARMY_CLOSE_COMBAT_RANGE
    base_speed: float = None
    spy_reveal_time: datetime = None

    view_width: int = None
    detailed_view_width: int = None
    aggressiveness: int = None
    forced_march: ForcedMarch = ForcedMarch.DEACTIVE
    removed: bool = False
    terrain_type: TerrainType = None

    air_parameters: AirParameters = None
    anti_air_parameters: AntiAirParameters = None

    carriable: bool = False
    carrier_feature: CarrierFeature = None

    last_location_ids: list[int] = None
    end_of_unit_walk: bool = False

    hit_points: float = None
    max_hit_points: int = None

    missile_carrier_feature: MissileCarrierFeature = None
    entrenched: bool = False

    next_anti_air_attack: datetime = None
    last_anti_air_attack: datetime = None
    last_anti_air_attack_distance: float = None
    last_damage_taken_time: datetime = None
    strength: float = None

    defence: float = None
    army_moral: float = None

    radar_signature_feature: RadarSignatureFeature = None
    token_feature: TokenFeature = None

    mapping = {
        "id": "id",
        "size": "s",
        "health": "h",
        "kills": "k",
        "owner_id": "o",
        "army_number": "an",
        "location_id": "l",
        "position": "p",
        "last_direction": "ld",
        "on_sea": "os",
        "at_airfield": "aa",
        "units": MappedValue("u", parse_units),
        "commands": MappedValue("c", parse_commands),
        "fight_status": "fs",
        "battle": "b",
        "attack_unit_id": "au",
        "attack_position": "ap",
        "next_attack_time": "na",
        "estimated_arrival_time": "at",
        "needs_rail": "nr",
        "needs_water": "nw",
        "has_stealth": "hs",
        "airplane": "a",
        "pre_fight_size": "ps",
        "pre_fight_type": "pt",
        "range": "r",
        "base_speed": "bs",
        "spy_reveal_time": "st",
        "view_width": "vw",
        "detailed_view_width": "dvw",
        "aggressiveness": "ag",
        "forced_march": "fm",
        "removed": "rm",
        "terrain_type": "tt",
        "air_parameters": "aip",
        "anti_air_parameters": "aap",
        "carriable": "ca",
        "carrier_feature": "cf",
        "last_location_ids": "ll",
        "end_of_unit_walk": "uw",
        "hit_points": "hp",
        "max_hit_points": "mhp",
        "missile_carrier_feature": "mc",
        "entrenched": "en",
        "next_anti_air_attack": "naa",
        "last_anti_air_attack": "laa",
        "last_anti_air_attack_distance": "laadist",
        "last_damage_taken_time": "ldt",
        "strength": "str",
        "defence": "def",
        "army_moral": "m",
        "radar_signature_feature": "rs",
        "token_feature": "tok",
    }
