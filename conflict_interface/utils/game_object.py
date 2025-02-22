from __future__ import annotations

from enum import Enum
from pprint import pprint
from typing import TYPE_CHECKING, get_origin, Union, get_args, Optional

if TYPE_CHECKING:
    from conflict_interface.game_interface import GameInterface
from typing import get_type_hints
from datetime import datetime, timedelta
from .json_mapped_class import JsonMappedClass, DefaultEnumMeta, ConMapping, JavaTypes
from .helper import unixtimestamp_to_datetime, seconds_to_timedelta

def to_list(name, value):
    res = []
    res.append(name)
    arr = []
    for v in value:
        if isinstance(v, GameObject):
            arr.append(v.to_dict())
        arr.append(v)
    res.append(arr)
    return res


def parse_list(obj, py_type: type, game):
    return [handle_normal(v, py_type.__args__[0], game) for v in obj[1]]

def parse_dict(obj, py_type: type, game):
    return {
        handle_normal(key, py_type.__args__[0], game) : handle_normal(value, py_type.__args__[1], game)
        for key, value in obj.items()
        if key != "@c"
    }

def handle_con_mapping(value, py_type, mapped_type):
    raise NotImplementedError


def handle_normal(value, py_type: type, game):
    print(value, py_type)
    if py_type == datetime:
        return unixtimestamp_to_datetime(value)
    elif py_type == timedelta:
        return seconds_to_timedelta(value)
    elif py_type in (bool, int, float, str):
        return py_type(value)
    elif issubclass(py_type, Enum):
        return py_type(int(value))
    elif issubclass(py_type, JsonMappedClass):
        return py_type.from_dict(value)
    elif issubclass(py_type, GameObject):
        return py_type.from_dict(value, game)
    elif py_type == list:
        raise NotImplementedError
    elif py_type == dict:
        raise NotImplementedError
    elif issubclass(py_type, list):
        return parse_list(value, py_type, game)
    elif issubclass(py_type, dict):
        return parse_dict(value, py_type, game)
    print(py_type == int)
    raise ValueError(f"Unknown type {py_type}")

def is_optional(tp):
    """Returns the underlying type if tp is typing.Optional, otherwise returns None."""
    if get_origin(tp) is Union:  # Check if it's a Union
        args = get_args(tp)  # Get the types inside the Union
        non_none_types = tuple(t for t in args if t is not type(None))  # Exclude NoneType
        if len(non_none_types) == 1:  # If it's exactly one type left, it's Optional
            return non_none_types[0]
    return None

def get_underlying_type(tp):
    """Returns the underlying type if tp is typing.Optional, otherwise returns None."""
    if get_origin(tp) is Union:  # Check if it's a Union
        args = get_args(tp)  # Get the types inside the Union
        non_none_types = tuple(t for t in args if t is not type(None))  # Exclude NoneType
        if len(non_none_types) == 1:  # If it's exactly one type left, it's Optional
            return non_none_types[0]
        else:
            return Union[[t for t in args if t is not type(None)]]
    return None

class GameObject(JsonMappedClass):
    """
    GameObject extends JsonMappedClass to include a reference
    to the central game instance, allowing subclasses to
    interact with game-wide data.
    """

    def __init__(self, game: GameInterface):
        """
        Initializes the GameObject with an optional reference
        to the game instance.

        Args:
            game (optional): The central game instance or None.
        """
        self.game = game  # Reference to the central game instance

    @classmethod
    def from_dict(cls, obj: dict, game: GameInterface = None):
        if not hasattr(cls, "MAPPING"):
            raise ValueError(f"{cls.__name__} has no MAPPING attribute")

        parsed_data = {}
        resolved = get_type_hints(cls)

        for py_name, mapped_value in cls.MAPPING.items():
            py_type = resolved[py_name]
            if mapped_value not in obj:
                if type(None) in get_args(py_type):
                    parsed_data[py_name] = None
                elif isinstance(py_type, DefaultEnumMeta):
                    parsed_data[py_name] = py_type()
                else:
                    raise ValueError(
                        f"Entry of type {py_type} cannot be parsed as object of type {cls} contains no key {mapped_value}")
            else:
                if is_optional(py_type):
                    py_type = get_underlying_type(py_type)
                if mapped_value is ConMapping and mapped_value.type != py_type:
                    parsed_data[py_name] = handle_con_mapping(obj[mapped_value.original], py_type, mapped_value.type)
                else:
                    parsed_data[py_name] = handle_normal(obj[mapped_value], py_type, game)
        pprint(cls)
        pprint(parsed_data)
        instance = cls(**parsed_data)
        instance.game = game
        return instance

    def to_dict(self):
        parsed_data = {}
        resolved = get_type_hints(self.__class__)
        for name, conflict_name in self.MAPPING.items():
            ftype = resolved[name]
            value = getattr(self, name)
            if isinstance(conflict_name, ConMapping):
                if isinstance(conflict_name.type, JavaTypes):
                    if conflict_name.type == JavaTypes.Vector:
                        parsed_data[conflict_name.original] = to_list("java.util.Vector", value)
                    elif conflict_name.type == JavaTypes.LinkedList:
                        parsed_data[conflict_name.original] = to_list("java.util.LinkedList", value)
                else:
                    parsed_data[conflict_name.original] = conflict_name.function()
            elif issubclass(ftype, GameObject):
                if value is None:
                    parsed_data[conflict_name] = None
                else:
                    parsed_data[conflict_name] = value.to_dict()
            elif issubclass(ftype, Enum):
                parsed_data[conflict_name] = value.value
            else:
                parsed_data[conflict_name] = value
        if hasattr(self, "C"):
            parsed_data["@c"] = getattr(self, "C")
        else:
            raise ValueError(self.__class__.__name__ + " has no C attribute")
        return parsed_data