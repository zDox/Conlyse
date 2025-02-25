from __future__ import annotations

from dataclasses import is_dataclass
from dataclasses import MISSING as DATACLASS_MISSING
from datetime import datetime, timedelta
from enum import Enum
from typing import TYPE_CHECKING, Any, cast, get_origin, Optional, get_args, Union
from typing import get_type_hints

from conflict_interface.data_types.custom_types import HashMap, ArrayList, HashSet, DefaultEnumMeta
from conflict_interface.data_types.point import Point
from conflict_interface.utils.helper import unix_to_datetime, seconds_to_timedelta


if TYPE_CHECKING:
    from conflict_interface.game_interface import GameInterface


def parse_conflict_mapping(cls,json_obj,game):
    parsed_data = {}
    for key, value in json_obj.items():
        if key == "@c":
            continue
        parsed_data[parse_any(cls.__args__[0],key , game)] = parse_any(cls.__args__[1],value , game)
    return HashMap(parsed_data)

def parse_conflict_array(cls, json_obj: list, game):
    return cls([parse_any(cls.__args__[0], v, game) for v in json_obj[1]])

def parse_normal_dict(cls,json_obj,game):
    parsed_data = {}
    for key, value in json_obj.items():
        parsed_data[parse_any(cls.__args__[0], key, game)] = parse_any(cls.__args__[1], value, game)
    return HashMap(parsed_data)

def parse_normal_list(cls, json_obj, game):
    return [parse_any(cls.__args__[0], v, game) for v in json_obj]

# Registry for direct type mappings
SIMPLE_TYPE_MAPPING: dict[type,Any] = {
    int: int,
    float: float,
    str: str,
    bool: bool,

    datetime: unix_to_datetime,
    timedelta: seconds_to_timedelta,
}
COMPLEX_TYPE_MAPPING: dict[type,Any] = {
    dict: parse_normal_dict,
    list: parse_normal_list,
    HashMap: parse_conflict_mapping,
    ArrayList: parse_conflict_array,
    HashSet: parse_conflict_array,
}





def parse_dataclass(cls: type, json_obj: dict, game: GameInterface = None) -> object:
    # --Error handling
    if not is_dataclass(cls):
        raise TypeError(f"{cls.__name__} must be a dataclass")
    if not hasattr(cls, "MAPPING"):
        raise ValueError(f"{cls.__name__} has no MAPPING implemented")
    # --End error handling

    var_type_dict = get_type_hints(cls)


    parsed_data = {}
    for python_var_name, conflict_var_name in getattr(cls,"MAPPING").items():
        python_var_type = var_type_dict[python_var_name]
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
                    raise ValueError(f"Field {python_var_name} is missing in {cls.__name__}")
            else:
                parsed_data[python_var_name] = field_info.default


    instance = cls(**parsed_data)
    return instance

def parse_game_object(cls: type[GameObject], json_obj: dict, game: GameInterface) -> GameObject:
    if game is None:
        raise ValueError(f"GameObject {cls} requires a game instance")

    instance = parse_dataclass(cls, json_obj, game)
    instance = cast(GameObject, instance)
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


def get_inner_type(cls: type, json_obj):
    # Check if the type is Optional
    origin = get_origin(cls)

    json_type = type(json_obj)

    if origin is Union:
        # Get the first argument of the Optional, which is the actual type
        args = get_args(cls)
        if args[0] is None:
            raise ValueError("Type is None, can't extract inner type.")

        for arg in args:
            if json_type is dict:
                if "@c" in json_obj:
                    if hasattr(arg, "C") and arg.C == json_obj["@c"]:
                        return arg
                elif json_type == arg:
                    return arg
                elif arg == Point and json_type.keys() == {"x", "y"}:
                    return arg
            elif arg is json_type:
                return arg

        raise ValueError(f"Unknown type {cls} for json_obj {str(json_obj)[:1000]}")

    elif cls is None:
        raise ValueError("Type is None, can't extract inner type.")
    else:
        return cls


def parse_any(cls: type, json_obj: Any, game: GameInterface = None) -> object:
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
    elif cls in SIMPLE_TYPE_MAPPING: # For basic types
        return SIMPLE_TYPE_MAPPING[cls](json_obj)
    elif get_origin(cls) in COMPLEX_TYPE_MAPPING: # For complex types, hashmap, dict etc
        return COMPLEX_TYPE_MAPPING[get_origin(cls)](cls, json_obj, game)
    else:
        raise ValueError(f"Unknown type {cls}: not in TYPE_MAPPING, origin is {get_origin(cls)}")




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
        return hash(self.__getattribute__(key) for key in self.MAPPING.keys())
