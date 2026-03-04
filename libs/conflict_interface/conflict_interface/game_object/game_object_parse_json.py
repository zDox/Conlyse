from __future__ import annotations

from dataclasses import dataclass
from dataclasses import is_dataclass
from dataclasses import MISSING as DATACLASS_MISSING
from enum import Enum
from logging import getLogger
from typing import Any
from typing import Callable
from typing import TYPE_CHECKING
from typing import cast
from typing import get_args
from typing import get_origin

from conflict_interface.game_object.game_object import GameObject
from conflict_interface.game_object.type_graph import TypeGraph
from conflict_interface.game_object.type_graph import TypeGraphNode

from conflict_interface.utils.enums import DefaultEnumMeta

if TYPE_CHECKING:
    from conflict_interface.interface import GameInterface

logger = getLogger()

_type_is_any_list_cache = {}
_type_is_list_cache = {}
_type_is_any_dict_cache = {}
_type_is_any_set_cache = {}
_type_is_game_object_cache = {}
_type_is_dataclass_cache = {}
_type_is_enum_cache = {}
_default_value_cache = {}


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

def get_fields(t: type[dataclass()], var: str):
    ret = t.__dataclass_fields__[var]
    return ret


def can_convert(value, value_type, cls) -> bool:# can you convert obj of type value_type to type cls?
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
        if value_type in (int, float):
            ok = value == int(value)
            return ok
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
    if cls is bool:
        if value_type is str:
            ok = value.lower() in {"true", "false", "1", "0"}
    #        timer_.split("BOOL FROM STR OK" if ok else "BOOL FROM STR FAIL")
            return ok
        #if value_type is int:
        #    ok = value in (0, 1)
    #        timer_.split("BOOL FROM INT OK" if ok else "BOOL FROM INT FAIL")
        #    return ok
    #    timer_.split("BOOL FAIL TYPE")
        return False

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


def _is_float_str(s: str) -> bool:
    """Check if a string is float-convertible without raising exceptions."""
    s = s.strip()
    if not s:
        return False
    if s.count('.') > 1 or s.lower() in ('inf', '-inf', '+inf', 'nan'):
        return False
    s_clean = s.lstrip('+-')
    return s_clean.replace('.', '', 1).isdigit()




class JsonParser:
    _PRIMITIVES = frozenset({int, float, str, bool, type(None)})
    PARSE_MAPPING: dict[int, dict[type, Callable]] = {}
    EDGE_CASES: dict[int, dict[str, type]] = {}
    GAME_STATES: dict[int, Any] = {}
    STATIC_MAP_DATAS: dict[int, Any] = {}

    @classmethod
    def register_game_state(cls, version: int, type_: type):
        cls.GAME_STATES.update({version: type_})

    @classmethod
    def register_static_map_data(cls, version: int, type_: type):
        cls.STATIC_MAP_DATAS.update({version: type_})

    @classmethod
    def register_custom_parser(cls, type_: type, version: int, func):
        #print(f"Registering custom parsers for type {type_}, version: {version}")
        cls.PARSE_MAPPING.setdefault(version, {})
        cls.PARSE_MAPPING[version][type_] = func

    @classmethod
    def register_edge_case(cls, tag: str, version: int, type_: type):
        cls.EDGE_CASES.setdefault(version, {})
        cls.EDGE_CASES[version][tag] = type_

    def __init__(self, version):
        self.version = version
        self.type_graph = TypeGraph(version)
        self.custom_parsers = self.PARSE_MAPPING.get(self.version, {})
        self.edge_cases = self.EDGE_CASES.get(self.version, {})
        self.static_map_data = self.STATIC_MAP_DATAS[version]
        self.game_state = self.GAME_STATES[version]



        self.custom_parsers.update(self.PARSE_MAPPING.get(-1, {}))
        self.edge_cases.update(self.EDGE_CASES.get(-1, {}))

    def parse_any(self, cls: Any, json_obj: dict | list | int | str, game: GameInterface = None):
        if cls not in self.type_graph.type_to_node:
            logger.warning(f"Trying to parse a type that is not used in any dataclass {cls}")
            self.type_graph.add_new_type_branch(cls)

        return self._parse_any(json_obj, [self.type_graph.type_to_node[cls]], game = game)

    def parse_game_state(self, json_obj, game):
        return self.parse_any(self.game_state, json_obj, game)

    def parse_static_map_data(self, json_obj):
        return self.parse_any(self.static_map_data, json_obj)

    def _parse_any(self, json_obj: dict | list | int | str, types: list[TypeGraphNode], game = None):
        #assert self.type_graph.build, "Build the type-tree using .build_tree before parsing!"
        correct_type_node = self.get_actual_type(json_obj, types)
        #if correct_type_node is None:
        #    raise ValueError(f"Type for {type(json_obj)} json_obj {str(json_obj)[:200]} could not be determined out of {[x.type for x in types]}")

        t = correct_type_node.type
        if json_obj is None:
            return None
        if t in self._PRIMITIVES:
            return t(json_obj)
        if t is type(None):
            return json_obj


        if type_is_game_object(t):
            return self.parse_game_object(json_obj, correct_type_node, game)

        elif type_is_dataclass(t):
            return self.parse_data_class(json_obj, correct_type_node)

        elif type_is_any_list(t) or type_is_any_set(t):
            if len(json_obj) == 0:
                return t([])

            if type_is_list(t):
                return self.parse_list(json_obj, correct_type_node.children["v"])

            # Edge case for SQl Date objects
            if get_origin(t) is self.edge_cases["SqlDate"]:
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
        elif t in self.custom_parsers:
            return self.custom_parsers[t](json_obj)
        else:
            raise ValueError(f"Cant parse json_obj {str(json_obj)[:200]} with type {t}")



    def parse_game_object(self, json_obj, t: TypeGraphNode, game):
        #assert type(json_obj) is dict, f"GameObject has to be represented by dict! type {t} is not; {str(json_obj)[:200]}"

        instance = self.parse_data_class(json_obj, t)
        instance = cast(t.type, instance)
        instance.game = game
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


            if conflict_var_name in json_obj:
                parsed_data[python_var_name] = self._parse_any(json_obj[conflict_var_name], t.children[python_var_name])
            else:
                if (cls, conflict_var_name) in _default_value_cache:
                    parsed_data[python_var_name] =  _default_value_cache[(cls, conflict_var_name)]
                else:
                    #possible_types = t.children[python_var_name]
                    #if len(possible_types) != 1:
                    #   raise ValueError(f"Default value for json_obj {str(json_obj)[:200]} could not be determined out of {[x.type for x in t.children[python_var_name]]}")
                    python_var_type = t.children[python_var_name][0].type
                    field_info = get_fields(cls, python_var_name)
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
                            raise ValueError(f"Field {python_var_name} is missing in {cls.__name__} (Might be optional), {str(json_obj)[:1000]}")
                    else:
                        parsed_data[python_var_name] = field_info.default

                    _default_value_cache[(cls, conflict_var_name)] = parsed_data[python_var_name]
        instance = cls(**parsed_data)
        return instance

    def parse_list(self, json_obj: list, value_t: list[TypeGraphNode]):
        return [self._parse_any(v, value_t) for v in json_obj]

    def parse_dict(self, json_obj: dict, key_t: list[TypeGraphNode], value_t: list[TypeGraphNode]):
        return {self._parse_any(k, key_t): self._parse_any(v, value_t) for k,v in json_obj.items()}

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
        # Fast path: 95%+ of calls have len(types) == 1 and are not a union
        if len(types) == 1:
            possible_type = types[0]
            # Skip _try_match_type overhead for common case
            if not possible_type.is_union:
                json_type = type(json_obj)

                # Fast path: exact type match for primitives
                if possible_type.type == json_type:
                    return possible_type

                # Type coercion (only if types don't match exactly)
                if json_type in self._PRIMITIVES:
                    return possible_type

                # Complex types
                if match := self._try_match_type(json_obj, possible_type):
                    return match
                raise ValueError(f"Type mismatch... {str(json_obj)[:200]}, {[str(x) for x in types]}")

        for possible_type in types:
            if match := self._try_match_type(json_obj, possible_type):
                return match

        raise ValueError(f"Type for {type(json_obj)} json_obj {str(json_obj)[:200]} could not be determined out of {[x.type for x in types]}")

    def _try_match_type(self, json_obj, possible_type: TypeGraphNode) -> TypeGraphNode | None:
        """Try to match json_obj against a single possible type."""

        # Handle union types recursively
        if possible_type.is_union:
            return self.get_actual_type(json_obj, possible_type.children["v"])

        json_type = type(json_obj)
        if json_type in self._PRIMITIVES:
            return self._match_primitive_type(json_obj, possible_type, json_type)
        # Dispatch to specific type handlers
        elif json_type is list:
            return self._match_list_type(json_obj, possible_type)
        elif json_type is dict:
            return self._match_dict_type(json_obj, possible_type)
        return None

    def _match_list_type(self, json_obj: list, possible_type: TypeGraphNode) -> TypeGraphNode | None:
        """Match list types with optional tagged discriminator."""
        # Check for tagged list (first element is type discriminator)
        if json_obj and possible_type.type in self.type_graph.type_to_c:
            if json_obj[0] in self.type_graph.type_to_c[possible_type.type]:

                return possible_type

        # Fall back to generic list type
        if type_is_list(possible_type.type):

            return possible_type

        return None

    def _match_dict_type(self, json_obj: dict, possible_type: TypeGraphNode) -> TypeGraphNode | None:
        """Match dict types with optional @c discriminator or structural checks."""
        # Check for explicit type discriminator
        if "@c" in json_obj:
            if possible_type.type in self.type_graph.type_to_c:
                if json_obj["@c"] in self.type_graph.type_to_c[possible_type.type]:
                    return possible_type

            return None


        # Check for generic dict type
        if type_is_any_dict(possible_type.type):

            return possible_type

        # Check for exact key match
        if type_is_dataclass(possible_type.type):

            assert hasattr(possible_type.type, "MAPPING")
            if set(json_obj.keys()) <= set(possible_type.type.MAPPING.values()):

                return possible_type
            else:
                print("For type: ", possible_type.type)
                print("Mapping is missing: ", [f"({x},{str(json_obj[x])[:100]})" for x in (set(json_obj.keys())- set(possible_type.type.MAPPING.values()))])
                print("Objs is missing   : ", [f"({x},{str(json_obj[x])[:100]})" for x in
                       ( set(possible_type.type.MAPPING.values())) - set(json_obj.keys()) ])

        return None

    def _match_primitive_type(self, json_obj, possible_type: TypeGraphNode, json_type: type) -> TypeGraphNode | None:

        """Match primitive types including datetime conversions."""
        # Direct type match
        if possible_type.type == json_type:
            return possible_type

        # Try datetime conversion
        if possible_type.type in self.custom_parsers:
            try:
                self.custom_parsers[possible_type.type](json_obj)
                return possible_type
            except ValueError:
                pass

        # Try general conversion
        if can_convert(json_obj, json_type, possible_type.type):
            return possible_type

        return None








