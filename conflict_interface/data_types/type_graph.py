
from collections import deque
from dataclasses import is_dataclass
from enum import Enum
from typing import Union
from typing import get_args
from typing import get_origin

from conflict_interface.data_types.game_object import GameObject


def type_is_union(t):
    return get_origin(t) is Union

def type_is_any_list(t):
    return t is list or get_origin(t) is list or issubclass(t, list)

def type_is_any_dict(t):
    return t is dict or get_origin(t) is dict or issubclass(t, dict)

def type_is_any_set(t):
    return t is set or get_origin(t) is set

def type_is_game_object(t):
    return issubclass(t, GameObject)

def type_is_dataclass(t):
    return is_dataclass(t)

def type_is_enum(t):
    return issubclass(t, Enum)

class TypeGraphNode:
    def __init__(self, _type: type):
        self.type: type = _type
        self.children: dict[str, list[TypeGraphNode]] = {}

class TypeGraph:

    _TYPE_QUE = deque([])
    def __init__(self):
        self.type_to_node: dict[type, TypeGraphNode] = {}
        self.type_to_c: dict[type, list[str]] = {}
        self.build = False

    @classmethod
    def register_type(cls, _type):
        cls._TYPE_QUE.append(_type)

    def build_graph(self):
        visited = set()
        while self._TYPE_QUE:
            _type = self._TYPE_QUE.pop()
            self.add_node(_type)

            try:
                mapping = _type.get_mapping()

            except AttributeError:
                mapping = getattr(_type, "MAPPING")


            type_hints = _type.get_type_hints_cached()


            for python_name in mapping.keys():
                t = type_hints[python_name]
                self.add_type_recursive(_type, t, python_name, visited)

        self.build = True

    def add_node(self, _type: type):
        if _type in self.type_to_node: return
        node = TypeGraphNode(_type)
        self.type_to_node[_type] = node
        if hasattr(_type, "C"):
            self.type_to_c.setdefault(_type, []).append(getattr(_type, "C"))

    def add_c_tag(self, _type: type, c):
        self.type_to_c.setdefault(_type, []).append(c)

    def add_edge_and_nodes(self, u: type, v: type, tag: str):
        self.add_node(u)
        self.add_node(v)
        self.type_to_node[u].children.setdefault(tag, []).append(self.type_to_node[v])

    def add_type_recursive(self, parent: type, nested_child: type, tag: str, visited):
        if (parent, nested_child, tag) in visited:
            return
        visited.add((parent, nested_child, tag))
        self.add_edge_and_nodes(parent, nested_child, tag)
        t: type = nested_child
        args = get_args(t)
        if type_is_union(t):
            for arg in args:
                self.add_type_recursive(nested_child, arg, "v", visited)

        elif type_is_any_dict(t):
            assert len(args) == 2
            self.add_type_recursive(nested_child, args[0], "k", visited)
            self.add_type_recursive(nested_child, args[1], "v", visited)

        elif type_is_any_list(t):
            assert len(args) == 1
            self.add_type_recursive(nested_child, args[0], "v", visited)

        elif type_is_any_set(t):
            assert len(args) == 1
            self.add_type_recursive(nested_child, args[0], "v", visited)

        elif type_is_game_object(t):
            if t is GameObject: return

            mapping = t.get_mapping()
            type_hints = t.get_type_hints_cached()

            for python_name in mapping.keys():
                type_hint = type_hints[python_name]
                self.add_type_recursive(nested_child, type_hint, python_name, visited)

        else:
            # Its a simple type
            assert get_origin(t) is None, f"{t} is not a simple type as assumed"
