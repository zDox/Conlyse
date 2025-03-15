from __future__ import annotations

from dataclasses import MISSING as DATACLASS_MISSING
from dataclasses import is_dataclass
from datetime import UTC
from enum import Enum
from typing import Any
from typing import TYPE_CHECKING
from typing import Type
from typing import Union
from typing import cast
from typing import get_args
from typing import get_origin
from typing import get_type_hints

from conflict_interface.data_types.custom_types import *
from conflict_interface.utils.helper import safe_issubclass

if TYPE_CHECKING: # The one place where this is needed for type hinting
    from conflict_interface.interface.game_interface import GameInterface

"""
Parsing: Json -> Python
Dumping: Python -> Json
"""
GameObjectType = TypeVar("GameObjectType", bound="GameObject")
DataclassType = TypeVar("DataclassType", bound="object")

def get_inner_type(cls: type, json_obj):
    # Check if the type is Optional
    origin = get_origin(cls)

    json_type = type(json_obj)

    if origin is Union:
        # Get the first argument of the Optional, which is the actual type
        args = get_args(cls)
        if args[0] is None:
            raise ValueError("Type is None, can't extract inner type.")
        if len(args) == 2 and args[1] is type(None):
            return args[0]

        for arg in args:
            if json_type is dict:
                if "@c" in json_obj:
                    if hasattr(arg, "C") and arg.C == json_obj["@c"]:
                        return arg
                elif json_type == arg:
                    return arg
                elif arg.__name__ == "Point" and json_obj.keys() == {"x", "y"}:
                    return arg
            elif json_type is list:
                if arg.C == json_obj[0]:
                    return arg
            elif json_type is int and arg is DateTimeMillisecondsInt: # TODO could run into problems when Union[int, DateTimeInt]
                return arg
            elif arg is json_type:
                return arg

        raise ValueError(f"Unknown type {cls} for json_obj {str(json_obj)[:1000]}, origin is {origin}, json_type is {json_type}")

    elif cls is None:
        raise ValueError("Type is None, can't extract inner type.")
    else:
        return cls

def parse_conflict_mapping(cls,json_obj,game):
    parsed_data = {}
    for key, value in json_obj.items():
        if key == "@c":
            continue
        parsed_data[parse_any(cls.__args__[0],key , game)] = parse_any(cls.__args__[1],value , game)
    return cls(parsed_data)

def parse_conflict_list(cls, json_obj: list, game):
    return cls([parse_any(cls.__args__[0], v, game) for v in json_obj[1]])

def parse_normal_dict(cls,json_obj,game):
    parsed_data = {}
    for key, value in json_obj.items():
        parsed_data[parse_any(cls.__args__[0], key, game)] = parse_any(cls.__args__[1], value, game)
    return cls(parsed_data)

def parse_normal_list(cls, json_obj, game):
    return [parse_any(cls.__args__[0], v, game) for v in json_obj]

def parse_date_time_milliseconds(json_obj):
    if len(str(json_obj)) < 13 and str(json_obj) != "0":
        raise ValueError(f"Expected int with at least 13 digits, got {len(str(json_obj))} digits {json_obj}")
    if type(json_obj) is str:
        return DateTimeMillisecondsStr.fromtimestamp(int(json_obj) / 1000, UTC)
    elif type(json_obj) is int:
        return DateTimeMillisecondsInt.fromtimestamp(int(json_obj) / 1000, UTC)
    else:
        raise ValueError(f"Expected int or str time, got {type(json_obj)}")

def parse_time_delta_milliseconds(json_obj):
    if type(json_obj) is str:
        return TimeDeltaMillisecondsStr(seconds=int(json_obj) / 1000)
    elif type(json_obj) is int:
        return TimeDeltaMillisecondsInt(seconds=int(json_obj) / 1000)
    else:
        raise ValueError(f"Expected int or str time, got {type(json_obj)}")

def parse_date_time_seconds(json_obj):
    if len(str(json_obj)) != 10 and str(json_obj) != "0":
        raise ValueError(f"Expected int with 10 digits, got {len(str(json_obj))} digits {json_obj}")
    if type(json_obj) is str:
        return DateTimeSecondsStr.fromtimestamp(int(json_obj), UTC)
    elif type(json_obj) is int:
        return DateTimeSecondsInt.fromtimestamp(int(json_obj), UTC)
    else:
        raise ValueError(f"Expected int or str time, got {type(json_obj)}")

def parse_time_delta_seconds(json_obj):
    if type(json_obj) is str:
        return TimeDeltaSecondsStr(seconds=int(json_obj))
    elif type(json_obj) is int:
        return TimeDeltaSecondsInt(seconds=int(json_obj))
    else:
        raise ValueError(f"Expected int or str time, got {type(json_obj)}")

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

def dump_conflict_mapping(obj) -> dict:
    if not hasattr(obj, "C"):
        raise ValueError(f"Object {obj} has no C implemented")

    json_obj = {"@c": obj.C}
    for key, value in obj.items():
        json_obj[str(dump_any(key))] = dump_any(value)

    return json_obj

# Registry for direct type mappings
SIMPLE_PARSE_MAPPING: dict[type,Any] = {
    int: int,
    float: float,
    str: str,
    bool: bool,

    DateTimeMillisecondsInt: parse_date_time_milliseconds,
    DateTimeMillisecondsStr: parse_date_time_milliseconds,
    TimeDeltaMillisecondsInt: parse_time_delta_milliseconds,
    TimeDeltaMillisecondsStr: parse_time_delta_milliseconds,
    DateTimeSecondsInt: parse_date_time_seconds,
    DateTimeSecondsStr: parse_date_time_seconds,
    TimeDeltaSecondsInt: parse_time_delta_seconds,
    TimeDeltaSecondsStr: parse_time_delta_seconds,
}
COMPLEX_PARSE_MAPPING: dict[type,Any] = {
    dict: parse_normal_dict,
    list: parse_normal_list,
    LinkedList: parse_conflict_list,
    Vector: parse_conflict_list,
    ArrayList: parse_conflict_list,
    ArraysArrayList: parse_conflict_list,
    EmptyList: parse_conflict_list,
    HashSet: parse_conflict_list,
    UnmodifiableSet: parse_conflict_list,
    UnmodifiableCollection: parse_conflict_list,
    UnitList: parse_conflict_list,
    BidListInner: parse_conflict_list,
    BidListOuter: parse_conflict_list,
    AskListInner: parse_conflict_list,
    AskListOuter: parse_conflict_list,
    ProductionList: parse_conflict_list,
    HashMap: parse_conflict_mapping,
    TreeMap: parse_conflict_mapping,
    LinkedHashMap: parse_conflict_mapping,
    RegularImmutableMap: parse_conflict_mapping,
    EmptyMap: parse_conflict_mapping,
    UnmodifiableMap: parse_conflict_mapping,

}

SIMPLE_DUMP_MAPPING: dict[type,Any] = {
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
    HashMap: dump_conflict_mapping,
    TreeMap: dump_conflict_mapping,
    LinkedHashMap: dump_conflict_mapping,
    RegularImmutableMap: dump_conflict_mapping,
    EmptyMap: dump_conflict_mapping,
    UnmodifiableMap: dump_conflict_mapping,

    DateTimeMillisecondsInt: dump_date_time_int,
    DateTimeMillisecondsStr: dump_date_time_str,
    TimeDeltaMillisecondsInt: dump_date_time_int,
    TimeDeltaMillisecondsStr: dump_date_time_str,
    DateTimeSecondsInt: dump_date_time_int,
    DateTimeSecondsStr: dump_date_time_str,
    TimeDeltaSecondsInt: dump_date_time_int,
    TimeDeltaSecondsStr: dump_date_time_str,
}

def parse_dataclass(cls: Type[DataclassType], json_obj: dict, game: GameInterface = None) -> DataclassType:
    # --Error handling
    if not is_dataclass(cls):
        raise TypeError(f"{cls.__name__} must be a dataclass")
    if not hasattr(cls, "MAPPING"):
        raise ValueError(f"{cls.__name__} has no MAPPING implemented")
    # --End error handling

    var_type_dict = get_type_hints(cls)

    if issubclass(cls, GameObject):
        mapping = cls.get_mapping()
    else:
        mapping = getattr(cls,"MAPPING")
    parsed_data = {}
    for python_var_name, conflict_var_name in mapping.items():
        python_var_type = var_type_dict[python_var_name]

        # if not has __dataclass_fields__ raise error
        if not hasattr(cls, "__dataclass_fields__"):
            raise ValueError(f"{cls.__name__} has no __dataclass_fields__")

        field_info = cls.__dataclass_fields__[python_var_name]


        if conflict_var_name in json_obj:
            parsed_data[python_var_name] = parse_any(python_var_type, json_obj[conflict_var_name], game)
        else:
            if field_info.default == DATACLASS_MISSING:
                if type(None) in get_args(python_var_type):
                    parsed_data[python_var_name] = None
                elif issubclass(python_var_type, Enum):
                    if isinstance(python_var_type, DefaultEnumMeta):
                        parsed_data[python_var_name] = python_var_type()
                    else:
                        raise ValueError(f"Enum {python_var_type} is not a DefaultEnumMeta")
                else:
                    print(f"Json obj: {json_obj}")
                    raise ValueError(f"Field {python_var_name} is missing in {cls.__name__} (Might be optional)")
            else:
                parsed_data[python_var_name] = field_info.default


    instance = cls(**parsed_data)
    return instance

def parse_game_object(cls: Type[GameObjectType], json_obj: dict, game: GameInterface) -> GameObjectType:
    if game is None:
        raise ValueError(f"GameObject {cls} requires a game instance")

    instance = parse_dataclass(cls, json_obj, game)
    instance = cast(GameObjectType, instance)
    instance.game = game
    return instance

def parse_enum(cls: type[Enum], json_obj: str | int) -> Enum:
    try:
        return cls(int(json_obj))
    except ValueError:
        try:
            return cls(json_obj)
        except ValueError:
            raise ValueError(f"Unknown enum value {json_obj} for {cls}")


def parse_any(cls: Type[DataclassType], json_obj: Any, game: GameInterface = None) -> DataclassType:
    if json_obj is None:
        return None
    if cls is None:
        raise ValueError(f"Type is None for json_obj {str(json_obj)[:1000]}")
    cls = get_inner_type(cls, json_obj)

    #print(f"Handling parse_any for {cls} and {str(json_obj)[:1000]}")

    if issubclass(cls, GameObject):
        return parse_game_object(cls, json_obj, game)
    elif is_dataclass(cls):
        return parse_dataclass(cls, json_obj, game)
    elif issubclass(cls, Enum):
        return parse_enum(cls, json_obj)
    elif cls in SIMPLE_PARSE_MAPPING: # For basic types
        # debug
        if SIMPLE_PARSE_MAPPING[cls] is int:
            if type(json_obj) is dict:
                raise ValueError(f"Expected int, got dict {json_obj}, cls is {cls}")

                    # end debug
        return SIMPLE_PARSE_MAPPING[cls](json_obj)
    elif get_origin(cls) in COMPLEX_PARSE_MAPPING: # For complex types, hashmap, dict etc
        return COMPLEX_PARSE_MAPPING[get_origin(cls)](cls, json_obj, game)
    else:
        raise ValueError(f"Unknown type {cls}: not in TYPE_MAPPING, origin is {get_origin(cls)}")


def dump_dataclass(obj: object) -> dict[str , Any]:
    if not is_dataclass(obj):
        raise TypeError(f"{type(obj).__name__} must be a dataclass")
    if not hasattr(obj, "MAPPING"):
        raise ValueError(f"{type(obj).__name__} has no MAPPING implemented")
    if not hasattr(obj, "C"):
        raise ValueError(f"{type(obj).__name__} has no C implemented")

    json_obj: dict = {"@c": getattr(obj, "C")}

    if issubclass(type(obj), GameObject):
        obj = cast(GameObject, obj)
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
    elif t in SIMPLE_DUMP_MAPPING:
        return SIMPLE_DUMP_MAPPING[t](obj)
    else:
        raise ValueError(f"Unknown type {t} for {obj} (not in SIMPLE_DUMP_MAPPING)")


class GameObject:
    """
    Base class for all game objects.
    """

    def __init__(self, game: GameInterface):
        """
        Initializes the GameObject with an optional reference
        to the game instance.

        Args:
            game (optional): The central game instance or None.
        """
        self.game = game  # Reference to the central game instance
        
    def __hash__(self):
        if not hasattr(self, "MAPPING"):
            raise ValueError(f"{type(self).__name__} has no MAPPING implemented")
        return hash(tuple(self.__getattribute__(key) for key in self.MAPPING.keys()))

    _mapping = {}
    @classmethod
    def get_mapping(cls):
        if not hasattr(cls, "MAPPING"):
            raise ValueError(f"{cls.__name__} has no MAPPING implemented")

        cls._mapping = cls.MAPPING
        for c in cls.__bases__:
            if c is GameObject:
                continue
            if issubclass(c, GameObject):
                cls._mapping = {**cls._mapping,
                                **c.get_mapping()}
        return cls._mapping

    def update(self, other):
        """
        Updates the current object with the values of another object.
        """
        if other is None:
            return

        if not issubclass(type(other), GameObject):
            raise ValueError(f"Can't update {type(self)} with {type(other)} not a game object")
        if type(self) != type(other):
            raise ValueError(f"Can't update {type(self)} with {type(other)} not of the same type")
        for key in self.get_mapping().keys():
            if getattr(other, key) is None:
                continue
            elif safe_issubclass(get_type_hints(type(self))[key], GameObject):
                if getattr(self, key) is None:
                    setattr(self, key, getattr(other, key))

                getattr(self, key).update(getattr(other, key))
            else:
                setattr(self, key, getattr(other, key))