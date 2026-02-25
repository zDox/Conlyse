
from collections import deque
from copy import deepcopy
from dataclasses import is_dataclass
from enum import Enum
from typing import Union
from typing import get_args
from typing import get_origin
from typing import get_type_hints

from conflict_interface.game_object.game_object import GameObject


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
    _PRIMITIVES = frozenset({int, float, str, bool, type(None)})

    def __init__(self, _type: type):
        self.type: type = _type
        self.children: dict[str, list[TypeGraphNode]] = {}

        self.is_union = type_is_union(_type)
        self.is_primitive = _type in self._PRIMITIVES

    def __str__(self):
        return f"| {self.type} | "



class TypeGraph:

    _TYPE_QUE = deque([])
    def __init__(self, version: int):
        self.type_to_node: dict[type, TypeGraphNode] = {}
        self.type_to_c: dict[type, list[str]] = {}
        self.build = False
        self.version = version
        self.visited = set()
        self._temp_type_que = deque([])

    @classmethod
    def register_type(cls, version, _type):
        cls._TYPE_QUE.append((version,_type))

    def build_graph(self):
        self._temp_type_que = deepcopy(self._TYPE_QUE)
        while self._temp_type_que:
            version, _type = self._temp_type_que.pop()

            if version != -1 and version != self.version:
                continue

            self.add_node(_type)

            try:
                mapping = _type.get_mapping()

            except AttributeError:
                mapping = getattr(_type, "MAPPING")

            try:
                type_hints = _type.get_type_hints_cached()
            except AttributeError:
                type_hints = get_type_hints(_type)


            for python_name in mapping.keys():

                t = type_hints[python_name]
                self.add_type_recursive(_type, t, python_name)

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

    def add_new_type_branch(self, new_type: type):
        t: type = new_type
        args = get_args(t)
        if type_is_union(t):
            for arg in args:
                self.add_type_recursive(new_type, arg, "v")

        elif type_is_any_dict(t):
            assert len(args) == 2, f"{t}"
            self.add_type_recursive(new_type, args[0], "k")
            self.add_type_recursive(new_type, args[1], "v")

        elif type_is_any_list(t):
            assert len(args) == 1
            self.add_type_recursive(new_type, args[0], "v")

        elif type_is_any_set(t):
            assert len(args) == 1
            self.add_type_recursive(new_type, args[0], "v")

        elif type_is_game_object(t):
            if t is GameObject: return

            mapping = t.get_mapping()
            type_hints = t.get_type_hints_cached()

            for python_name in mapping.keys():
                type_hint = type_hints[python_name]
                self.add_type_recursive(new_type, type_hint, python_name)

        else:
            # Its a simple type
            assert get_origin(t) is None, f"{t} is not a simple type as assumed"

    def add_type_recursive(self, parent: type, nested_child: type, tag: str):
        if (parent, nested_child, tag) in self.visited:
            return
        self.visited.add((parent, nested_child, tag))
        self.add_edge_and_nodes(parent, nested_child, tag)
        self.add_new_type_branch(nested_child)


