import dataclasses
from dataclasses import MISSING as DATACLASS_MISSING
from dataclasses import is_dataclass
from datetime import UTC
from enum import Enum
from logging import getLogger
from typing import Union
from typing import cast
from typing import get_args
from typing import get_origin

from conflict_interface.data_types.custom_types import DateTimeMillisecondsInt
from conflict_interface.data_types.custom_types import DateTimeMillisecondsStr
from conflict_interface.data_types.custom_types import DateTimeSecondsInt
from conflict_interface.data_types.custom_types import DateTimeSecondsStr
from conflict_interface.data_types.custom_types import DefaultEnumMeta
from conflict_interface.data_types.custom_types import SqlDate
from conflict_interface.data_types.custom_types import TimeDeltaMillisecondsInt
from conflict_interface.data_types.custom_types import TimeDeltaMillisecondsStr
from conflict_interface.data_types.custom_types import TimeDeltaSecondsInt
from conflict_interface.data_types.custom_types import TimeDeltaSecondsStr
from conflict_interface.data_types.game_object import GameObject
from conflict_interface.data_types.point import Point
from conflict_interface.data_types.type_graph import TypeGraph
from conflict_interface.data_types.type_graph import TypeGraphNode
from performance_tests.split_timer import SplitTimer

logger = getLogger()

_is_union_cache = {}
_type_is_any_list_cache = {}
_type_is_list_cache = {}
_type_is_any_dict_cache = {}
_type_is_any_set_cache = {}
_type_is_game_object_cache = {}
_type_is_dataclass_cache = {}
_type_is_enum_cache = {}

def type_is_union(t):
    try:
        return _is_union_cache[t]
    except KeyError:
        pass
    ret = get_origin(t) is Union
    _is_union_cache[t] = ret
    return ret

def type_is_any_list(t):
    try:
        return _type_is_any_list_cache[t]
    except KeyError:
        pass
    ret = t is list or get_origin(t) is list or issubclass(t, list)
    _type_is_any_list_cache[t] = ret
    return ret

def type_is_list(t):
    try:
        return _type_is_list_cache[t]
    except KeyError:
        pass
    ret = t is list or get_origin(t) is list
    _type_is_list_cache[t] = ret
    return ret

def type_is_any_dict(t):
    try:
        return _type_is_any_dict_cache[t]
    except KeyError:
        pass
    ret = t is dict or get_origin(t) is dict or issubclass(t, dict)
    _type_is_any_dict_cache[t] = ret
    return ret

def type_is_any_set(t):
    try:
        return _type_is_any_set_cache[t]
    except KeyError:
        pass
    ret = t is set or get_origin(t) is set
    _type_is_any_set_cache[t] = ret
    return ret

def type_is_game_object(t):
    try:
        return _type_is_game_object_cache[t]
    except KeyError:
        pass
    ret = issubclass(t, GameObject)
    _type_is_game_object_cache[t] = ret
    return ret

def type_is_dataclass(t):
    try:
        return _type_is_dataclass_cache[t]
    except KeyError:
        pass
    ret = is_dataclass(t)
    _type_is_dataclass_cache[t] = ret
    return ret

def type_is_enum(t):
    try:
        return _type_is_enum_cache[t]
    except KeyError:
        pass
    ret = issubclass(t, Enum)
    _type_is_enum_cache[t] = ret
    return ret

def get_fields(t: type[dataclasses.dataclass()], var: str):
    ret = t.__dataclass_fields__[var]
    return ret


def can_convert(value, value_type, cls) -> bool:
    """
    Handles Pyton / JavaScript type conversion quirks. Commented Cases do not appear yet and are removed for performance

    Args:
        value: Json Obj to convert
        value_type: Type of Json Obj
        cls: Cls to convert to

    Returns: True if value can be converted to cls

    """
    # ---------- SAME TYPE ----------
    #if value_type is cls:
    #    timer_.split("SAME TYPE")
    #    return True

    # ---------- STRING ----------
    if cls is str:
        return True  # everything can be stringified

    # ---------- INT ----------
    if cls is int:
        #if value_type is bool:  # bool is subclass of int, usually unwanted
        #    timer_.split("INT FAIL BOOL")
        #    return False
        #if value_type in (int, float):
        #    ok = value == int(value)
        #    timer_.split("INT FROM NUM OK" if ok else "INT FROM NUM FAIL")
        #    return ok
        if value_type is str:
            ok = value.strip().lstrip("+-").isdigit()
            return ok
        #timer_.split("INT FAIL TYPE")
        return False

    # ---------- FLOAT ----------
    if cls is float:
        if value_type in (int, float):
            return True
        if value_type is str:
            try:
                float(value)
                return True
            except ValueError:
                return False
        #timer_.split("FLOAT FAIL TYPE")
        return False

    # ---------- BOOL ----------
    #if cls is bool:
    #    if value_type is str:
    #        ok = value.lower() in {"true", "false", "1", "0"}
    #        timer_.split("BOOL FROM STR OK" if ok else "BOOL FROM STR FAIL")
    #        return ok
    #    if value_type is int:
    #        ok = value in (0, 1)
    #        timer_.split("BOOL FROM INT OK" if ok else "BOOL FROM INT FAIL")
    #        return ok
    #    timer_.split("BOOL FAIL TYPE")
    #    return False

    # ---------- ENUM ----------
    if type_is_enum(cls):
        # direct value match
        if value in cls._value2member_map_:
            return True

        # string name or numeric string
        if value_type is str:
            #if value in cls.__members__:
            #    timer_.split("ENUM NAME")
            #    return True
            try:
                num = int(value)
            except ValueError:
                #timer_.split("ENUM STR FAIL PARSE")
                return False
            ok = num in cls._value2member_map_
            return ok

        #timer_.split("ENUM FAIL TYPE")
        return False

    # ---------- FALLBACK ----------
    try:
        cls(value)
        return True
    except (TypeError, ValueError):
        return False



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



DATETIME_MAPPING = {
    DateTimeMillisecondsInt: parse_date_time_milliseconds,
    DateTimeMillisecondsStr: parse_date_time_milliseconds,
    TimeDeltaMillisecondsInt: parse_time_delta_milliseconds,
    TimeDeltaMillisecondsStr: parse_time_delta_milliseconds,
    DateTimeSecondsInt: parse_date_time_seconds,
    DateTimeSecondsStr: parse_date_time_seconds,
    TimeDeltaSecondsInt: parse_time_delta_seconds,
    TimeDeltaSecondsStr: parse_time_delta_seconds,
}


class JsonParser:
    _PRIMITIVES = frozenset({int, float, str, bool, type(None)})

    def __init__(self):
        self.type_graph = TypeGraph()

    def parse_any(self, json_obj: dict | list | int | str, types: list[TypeGraphNode]):
        #assert self.type_graph.build, "Build the type-tree using .build_tree before parsing!"
        correct_type_node = self.get_actual_type(json_obj, types)
        #if correct_type_node is None:
        #    raise ValueError(f"Type for {type(json_obj)} json_obj {str(json_obj)[:200]} could not be determined out of {[x.type for x in types]}")

        t = correct_type_node.type
        if t in self._PRIMITIVES:
            return json_obj

        if type_is_game_object(t):
            return self.parse_game_object(json_obj, correct_type_node)

        elif type_is_dataclass(t):
            return self.parse_data_class(json_obj, correct_type_node)

        elif type_is_any_list(t) or type_is_any_set(t):
            if len(json_obj) == 0:
                return t([])

            if type_is_list(t):
                return self.parse_list(json_obj, correct_type_node.children["v"])

            # Edge case for SQl Date objects
            if get_origin(t) is SqlDate:
                return t(self.parse_list(json_obj[1:], correct_type_node.children["v"]))

            return t(self.parse_list(json_obj[1], correct_type_node.children["v"]))

        elif type_is_any_dict(t):
            if "@c" in json_obj:
                json_obj.pop("@c")
            return t(self.parse_dict(json_obj,
                            correct_type_node.children["k"],
                            correct_type_node.children["v"]))
        elif type_is_enum(t):
            return self.parse_enum(json_obj, t)
        elif t in DATETIME_MAPPING:
            return DATETIME_MAPPING[t](json_obj)
        else:
            raise ValueError(f"Cant parse json_obj {str(json_obj)[:200]} with type {t}")


    def parse_game_object(self, json_obj, t: TypeGraphNode):
        assert type(json_obj) is dict, f"GameObject has to be represented by dict! type {t} is not; {str(json_obj)[:200]}"

        instance = self.parse_data_class(json_obj, t)
        instance = cast(t.type, instance)
        # TODO add Game
        return instance

    def parse_data_class(self, json_obj, t: TypeGraphNode):
        cls = t.type

        # --Error handling

        #if not is_dataclass(cls):
        #    raise TypeError(f"{cls.__name__} must be a dataclass")
        #if not hasattr(cls, "MAPPING"):
        #    raise ValueError(f"{cls.__name__} has no MAPPING implemented")
        # --End error handling

        if type_is_game_object(cls):
            mapping = cls.get_mapping()
        else:
            mapping = getattr(cls, "MAPPING")

        parsed_data = {}
        for python_var_name, conflict_var_name in mapping.items():
            # if not has __dataclass_fields__ raise error
            #if not hasattr(cls, "__dataclass_fields__"):
            #    raise ValueError(f"{cls.__name__} has no __dataclass_fields__")

            field_info = get_fields(cls, python_var_name)
            if conflict_var_name in json_obj:
                parsed_data[python_var_name] = self.parse_any(json_obj[conflict_var_name], t.children[python_var_name])
            else:
                #possible_types = t.children[python_var_name]
                #if len(possible_types) != 1:
                #    raise ValueError(f"Default value for json_obj {str(json_obj)[:200]} could not be determined out of {[x.type for x in t.children[python_var_name]]}")
                python_var_type = t.children[python_var_name][0].type

                if field_info.default == DATACLASS_MISSING:
                    if field_info.default_factory != DATACLASS_MISSING:
                        parsed_data[python_var_name] = field_info.default_factory()
                    elif type(None) in get_args(python_var_type):
                        parsed_data[python_var_name] = None
                    elif issubclass(python_var_type, Enum):
                        if isinstance(python_var_type, DefaultEnumMeta):
                            parsed_data[python_var_name] = python_var_type()
                        else:
                            raise ValueError(f"Enum {python_var_type} is not a DefaultEnumMeta")
                    else:
                        raise ValueError(f"Field {python_var_name} is missing in {cls.__name__} (Might be optional)")
                else:
                    parsed_data[python_var_name] = field_info.default
        instance = cls(**parsed_data)
        return instance

    def parse_list(self, json_obj: list, value_t: list[TypeGraphNode]):
        return [self.parse_any(v, value_t) for v in json_obj]

    def parse_dict(self, json_obj: dict, key_t: list[TypeGraphNode], value_t: list[TypeGraphNode]):
        return {self.parse_any(k, key_t): self.parse_any(v, value_t) for k,v in json_obj.items()}

    @staticmethod
    def parse_enum(json_obj: str | int, t: type) -> Enum:
        try:
            return t(int(json_obj))
        except ValueError:
            try:
                return t(json_obj)
            except ValueError:
                raise ValueError(f"Unknown enum value {json_obj} for {t}")

    def get_actual_type(self, json_obj, types: list[TypeGraphNode]) -> TypeGraphNode | None:
        for possible_type in types:
            if match := self._try_match_type(json_obj, possible_type):
                return match

        raise ValueError(f"Type for {type(json_obj)} json_obj {str(json_obj)[:200]} could not be determined out of {[x.type for x in types]}")

    def _try_match_type(self, json_obj, possible_type: TypeGraphNode) -> TypeGraphNode | None:
        """Try to match json_obj against a single possible type."""

        # Handle union types recursively
        if type_is_union(possible_type.type):
            return self.get_actual_type(json_obj, possible_type.children["v"])

        json_type = type(json_obj)

        # Dispatch to specific type handlers
        if json_type is list:
            return self._match_list_type(json_obj, possible_type)
        elif json_type is dict:
            return self._match_dict_type(json_obj, possible_type)
        else:
            return self._match_primitive_type(json_obj, possible_type, json_type)

    def _match_list_type(self, json_obj: list, possible_type: TypeGraphNode) -> TypeGraphNode | None:
        """Match list types with optional tagged discriminator."""
        # Check for tagged list (first element is type discriminator)
        if json_obj and possible_type.type in self.type_graph.type_to_c:
            if json_obj[0] == self.type_graph.type_to_c[possible_type.type]:

                return possible_type

        # Fall back to generic list type
        if type_is_list(possible_type.type):

            return possible_type

        return None

    def _match_dict_type(self, json_obj: dict, possible_type: TypeGraphNode) -> TypeGraphNode | None:

        """Match dict types with optional @c discriminator or structural checks."""
        # Check for explicit type discriminator
        if "@c" in json_obj and possible_type.type in self.type_graph.type_to_c:
            if json_obj["@c"] == self.type_graph.type_to_c[possible_type.type]:
                return possible_type

        # Check for generic dict type
        if type_is_any_dict(possible_type.type):

            return possible_type

        # Special case: Point type with exact structure
        if possible_type.type is Point and json_obj.keys() == {"x", "y"}:

            return possible_type

        return None

    def _match_primitive_type(self, json_obj, possible_type: TypeGraphNode, json_type: type) -> TypeGraphNode | None:

        """Match primitive types including datetime conversions."""
        # Direct type match
        if possible_type.type == json_type:
            return possible_type

        # Try datetime conversion
        if possible_type.type in DATETIME_MAPPING:
            try:
                DATETIME_MAPPING[possible_type.type](json_obj)
                return possible_type
            except ValueError:
                pass

        # Try general conversion
        if can_convert(json_obj, json_type, possible_type.type):
            return possible_type

        return None











