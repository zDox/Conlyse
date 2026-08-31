from dataclasses import is_dataclass
from enum import Enum
from typing import Any

from conflict_interface.game_object.game_object import GameObject
from .custom_types import ArrayList
from .custom_types import ArraysArrayList
from .custom_types import AskListInner
from .custom_types import AskListOuter
from .custom_types import BidListInner
from .custom_types import BidListOuter
from .custom_types import DateTimeMillisecondsInt
from .custom_types import DateTimeMillisecondsStr
from .custom_types import DateTimeSecondsInt
from .custom_types import DateTimeSecondsStr
from .custom_types import EmptyList
from .custom_types import EmptyMap
from .custom_types import HashMap
from .custom_types import HashSet
from .custom_types import HashSetMap
from .custom_types import LinkedHashMap
from .custom_types import LinkedList
from .custom_types import ProductionList
from .custom_types import RankingEntryList
from .custom_types import RegularImmutableMap
from .custom_types import SqlDate
from .custom_types import TimeDeltaMillisecondsInt
from .custom_types import TimeDeltaMillisecondsStr
from .custom_types import TimeDeltaSecondsInt
from .custom_types import TimeDeltaSecondsStr
from .custom_types import TreeMap
from .custom_types import UnitList
from .custom_types import UnmodifiableCollection
from .custom_types import UnmodifiableMap
from .custom_types import UnmodifiableSet
from .custom_types import Vector


def to_json(cls: Any):
    return dump_any(cls)

def dump_date_time_int(obj) -> int:
    t: type = type(obj)
    if t is DateTimeMillisecondsInt:
        return int(obj.timestamp() * 1000)
    elif t is TimeDeltaMillisecondsInt:
        return int(obj.total_seconds() * 1000)
    elif t is DateTimeSecondsInt:
        return int(obj.timestamp())
    elif t is TimeDeltaSecondsInt:
        return int(obj.total_seconds())
    else:
        raise ValueError(f"Unknown type {t} for {obj} (expected DateTimeInt or TimeDeltaInt)")


def dump_date_time_str(obj) -> str:
    t: type = type(obj)
    if t is DateTimeMillisecondsStr:
        return str(int(obj.timestamp() * 1000))
    elif t is TimeDeltaMillisecondsStr:
        return str(int(obj.total_seconds() * 1000))
    elif t is DateTimeSecondsStr:
        return str(int(obj.timestamp()))
    elif t is TimeDeltaSecondsStr:
        return str(int(obj.total_seconds()))
    else:
        raise ValueError(f"Unknown type {t} for {obj} (expected DateTimeStr or TimeDeltaStr)")


def dump_normal_dict(obj) -> dict:
    return {str(dump_any(k)): dump_any(v) for k, v in obj.items()}


def dump_normal_list(obj) -> list:
    return [dump_any(v) for v in obj]


def dump_conflict_list(obj) -> list:
    if not hasattr(obj, "C"):
        raise ValueError(f"Object {obj} has no C implemented")

    return [obj.C, [dump_any(v) for v in obj]]


def dump_sql_date(obj) -> list:
    if not hasattr(obj, "C"):
        raise ValueError(f"Object {obj} has no C implemented")

    return [obj.C] + [dump_any(v) for v in obj]


def dump_conflict_mapping(obj) -> dict:
    if not hasattr(obj, "C"):
        raise ValueError(f"Object {obj} has no C implemented")

    json_obj = {"@c": obj.C}
    for key, value in obj.items():
        json_obj[str(dump_any(key))] = dump_any(value)

    return json_obj


def dump_dict_to_list(obj) -> list:
    if not hasattr(obj, "C"):
        raise ValueError(f"Object {obj} has no C implemented")

    return [obj.C, [dump_any(v) for v in obj.values()]]

DUMP_MAPPING: dict[type,Any] = {
    int: int,
    float: float,
    str: str,
    bool: bool,
    list: dump_normal_list,
    dict: dump_normal_dict,
    Vector: dump_conflict_list,
    LinkedList: dump_conflict_list,
    ArrayList: dump_conflict_list,
    ArraysArrayList: dump_conflict_list,
    EmptyList: dump_conflict_list,
    HashSet: dump_conflict_list,
    UnmodifiableSet: dump_conflict_list,
    UnmodifiableCollection: dump_conflict_list,
    UnitList: dump_conflict_list,
    ProductionList: dump_conflict_list,
    BidListInner: dump_conflict_list,
    BidListOuter: dump_conflict_list,
    AskListInner: dump_conflict_list,
    AskListOuter: dump_conflict_list,
    RankingEntryList: dump_conflict_list,
    HashMap: dump_conflict_mapping,
    TreeMap: dump_conflict_mapping,
    LinkedHashMap: dump_conflict_mapping,
    RegularImmutableMap: dump_conflict_mapping,
    EmptyMap: dump_conflict_mapping,
    UnmodifiableMap: dump_conflict_mapping,
    HashSetMap: dump_dict_to_list,
    SqlDate: dump_sql_date,

    DateTimeMillisecondsInt: dump_date_time_int,
    DateTimeMillisecondsStr: dump_date_time_str,
    TimeDeltaMillisecondsInt: dump_date_time_int,
    TimeDeltaMillisecondsStr: dump_date_time_str,
    DateTimeSecondsInt: dump_date_time_int,
    DateTimeSecondsStr: dump_date_time_str,
    TimeDeltaSecondsInt: dump_date_time_int,
    TimeDeltaSecondsStr: dump_date_time_str,
}

def dump_dataclass(obj: object) -> dict[str , Any]:
    if not is_dataclass(obj):
        raise TypeError(f"{type(obj).__name__} must be a dataclass")
    if not hasattr(obj, "MAPPING"):
        raise ValueError(f"{type(obj).__name__} has no MAPPING implemented")
    if not hasattr(obj, "C"):
        raise ValueError(f"{type(obj).__name__} has no C implemented")

    json_obj: dict = {"@c": getattr(obj, "C")}

    if issubclass(type(obj), GameObject):
        mapping = obj.get_mapping()
    else:
        mapping = getattr(type(obj), "MAPPING")

    for python_var_name, conflict_var_name in mapping.items():
        json_obj[conflict_var_name] = dump_any(getattr(obj, python_var_name))

    return json_obj

def dump_any(obj: Any) -> Any:
    t: type = type(obj)
    if obj is None:
        return None
    elif t.__name__ == "Point": # Has to be in front of is_dataclass
        return {"x": obj.x, "y": obj.y}
    elif is_dataclass(obj):
        return dump_dataclass(obj)
    elif issubclass(t, Enum):
        return obj.value
    elif t in DUMP_MAPPING:
        return DUMP_MAPPING[t](obj)
    else:
        raise ValueError(f"Unknown type {t} for {obj} (not in SIMPLE_DUMP_MAPPING)")