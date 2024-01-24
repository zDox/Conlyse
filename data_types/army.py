from data_types.utils import JsonMappedClass, MappedValue, Position, \
        DefaultEnumMeta, unixtimestamp_to_datetime
from data_types.warfare_unit import Unit
from data_types.province import TerrainType
from data_types.features import CarrierFeature, MissileCarrierFeature, \
        RadarSignatureFeature, TokenFeature

from dataclasses import dataclass
from datetime import date
from enum import Enum


def parse_units(value: list):
    if value is None:
        return

    return [Unit.from_dict(unit) for unit in value[1]]


def parse_commands(value: list):
    if value is None:
        return

    return [Command.from_dict(command) for command in value[1]]


@dataclass
class Command(JsonMappedClass):
    mapping = {}


@dataclass
class Battle(JsonMappedClass):
    mapping = {}


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


@dataclass
class AirParameters:
    mapping = {}


@dataclass
class AntiAirParameters:
    mapping = {}


@dataclass
class Army(JsonMappedClass):
    id: int
    size: int
    health: int
    kills: int
    owner_id: int
    army_number: int
    location_id: int
    position: Position
    last_direction: Position
    on_sea: bool
    at_airfield: bool
    units: list[Unit]

    commands: list[GotoCommand | RetreatCommand | AttackCommand |
                   SiegeCommand | PatrolCommand | WaitCommand |
                   SplitArmyCommand | FireMissileCommand]
    fight_status: FightStatus
    battle: Battle
    attack_unit_id: int
    attack_position: Position
    next_attack_time: date
    estimated_arrival_time: date

    needs_rail: bool  # I do not now any unit which needs rail but whatever
    needs_water: bool
    has_stealth: bool
    airplane: bool

    pre_fight_size: int
    pre_fight_type: int

    range: int
    base_speed: float
    spy_reveal_time: date

    view_width: int
    detailed_view_width: int
    aggressiveness: int
    forced_march: ForcedMarch
    removed: bool
    terrain_type: TerrainType

    air_parameters: AirParameters
    anti_air_parameters: AntiAirParameters

    carriable: bool
    carrier_feature: CarrierFeature

    last_location_ids: list[int]
    end_of_unit_walk: bool

    hit_points: int
    max_hit_points: int

    missile_carrier_feature: MissileCarrierFeature
    entrenched: bool

    next_anti_air_attack: date
    last_anti_air_attack: date
    last_anti_air_attack_distance: float
    last_damage_taken_time: date
    strength: float

    defence: float
    army_moral: float

    radar_signature_feature: RadarSignatureFeature
    token_feature: TokenFeature

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
        "spy_reveal_time": MappedValue("st", unixtimestamp_to_datetime),
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
        "next_anti_air_attack": MappedValue("naa", unixtimestamp_to_datetime),
        "last_anti_air_attack": MappedValue("laa", unixtimestamp_to_datetime),
        "last_anti_air_attack_distance": "laadist",
        "last_damage_taken_time": MappedValue("ldt",
                                              unixtimestamp_to_datetime),
        "strength": "str",
        "defence": "def",
        "army_moral": "m",
        "radar_signature_feature": "rs",
        "token_feature": "tok",
    }
