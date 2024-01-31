from dataclasses import dataclass
from enum import Enum

from data_types.utils import JsonMappedClass, MappedValue


class UnitFeature(Enum):
    SHIP = 10,
    RAILBOUND = 11,
    AIRPLANE = 12,
    STEALTH = 13,
    NAMED = 14,
    AGGRESSIVENESS = 15,
    MORALE = 16,
    SCOUT = 17,
    SIEGE = 18,
    STORM = 19,
    FASTFLIGHT = 20,
    AIRPLANE_CARRIER = 21,
    KAMIKAZE = 22,
    ROCKET = 23,
    ATOMIC_BOMB = 24,
    CIVILIAN = 25,
    LAND_EXPLORER = 26,
    SEA_EXPLORER = 27,
    CARRIABLE = 28,
    FLANK = 29,
    FRONT = 30,
    BACK = 31,
    ADMINISTRATOR = 32,
    COLONIST = 33,
    SINGLE_REQUIREMENT = 34,
    REQUIRED_BUILDING_AS_FACTORY = 35,
    UNITFEATURE_CAN_RETREAT = 37,
    UNITFEATURE_MISSILE_CARRIER = 38,
    UNITFEATURE_MISSILE = 39,
    UNITFEATURE_CONVERT_TO_RESOURCE = 40,
    UNITFEATURE_FERRY_RANGE = 41,
    UNITFEATURE_HAS_RADAR = 42,
    UNITFEATURE_VISIBLE_ON_RADAR = 43,
    UNITFEATURE_ANTI_AIR = 44,
    UNITFEATURE_AIR_MOBILE = 45,
    UNITFEATURE_AIR_TRANSPORT = 46,
    UNITFEATURE_NOT_PRODUCABLE = 47,
    UNITFEATURE_CANNOT_CONQUER = 48,
    UNITFEATURE_CAN_EMBARK = 49,
    UNITFEATURE_AIR_TRANSPORTABLE = 50,
    UNITFEATURE_PUBLICLY_VISIBLE = 51,
    UNITFEATURE_NEWS_INITIATE_ARTICLE_CATEGORY = 52,
    UNITFEATURE_NEWS_ATTACK_ARTICLE_CATEGORY = 53,
    UNITFEATURE_REBEL = 54,
    UNITFEATURE_MORALE_IMPACT_FACTOR = 55,
    UNITFEATURE_CAMOUFLAGE = 56,
    UNITFEATURE_NOTIFICATION_TEXT = 57,
    UNITFEATURE_ARMY_BOOST = 58,
    UNITFEATURE_LIMITED_MOBILIZATION = 59,
    UNITFEATURE_TOKEN_PRODUCER = 60,
    UNITFEATURE_TOKEN_CONSUMER = 61,
    UNITFEATURE_DISBANDABLE = 62


class MissileType(Enum):
    BALLISTIC = 1
    CRUISE = 2







@dataclass
class Unit(JsonMappedClass):
    id: int
    unit_type: int
    health: float
    size: int
    kills: int
    camoflage_replacement_unit: int
    on_sea: bool
    at_airfield: bool
    hit_points: float
    max_hit_points: int

    mapping = {
        "id": "id",
        "unit_type": "t",
        "health": "h",
        "size": "s",
        "kills": "k",
        "camoflage_replacement_unit": "cru",
        "on_sea": "os",
        "at_airfield": "aa",
        "hit_points": "hp",
        "max_hit_points": "mhp",
    }


def parse_unit(obj):
    if obj is None:
        return
    return Unit.from_dict(obj)


@dataclass
class SpecialUnit(JsonMappedClass):
    enabled: bool
    constructing: bool
    unit: Unit
    original_unit: Unit

    mapping = {
        "enabled": "e",
        "constructing": "cn",
        "unit": MappedValue("unit", parse_unit),
        "original_unit": MappedValue("originalUnit", parse_unit),
    }
