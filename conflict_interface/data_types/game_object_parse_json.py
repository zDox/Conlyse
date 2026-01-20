from collections import deque
from logging import getLogger
from typing import Union
from typing import cast
from typing import get_args
from typing import get_origin
from typing import get_type_hints

from conflict_interface.data_types.game_object import GameObject

logger = getLogger()

def is_union(t):
    return get_origin(t) is Union

def is_optional(t):
    origin = get_origin(t)
    if origin is Union:
        args = get_args(t)
        return type(None) in args  # Optional[T] has None in the Union
    return False

def is_list(t):
    return t is list or get_origin(t) is list or issubclass(t, list)

def is_dict(t):
    return t is dict or get_origin(t) is dict or issubclass(t, dict)

def is_set(t):
    return t is set or get_origin(t) is set

def is_game_object(t):
    return issubclass(t, GameObject)

class TypeGraphNode:
    def __init__(self, _type: type):
        self.type: type = _type
        self.children: dict[str, list[TypeGraphNode]] = {}

class TypeGraph:
    def __init__(self):
        self.root = None
        self.type_to_node: dict[type, TypeGraphNode] = {}

    def add_node(self, _type: type):
        node = TypeGraphNode(_type)
        if self.root is None:
            self.root = node
        self.type_to_node[_type] = node

    def add_edge_and_nodes(self, u: type, v: type, tag: str):
        if u not in self.type_to_node:
            self.add_node(u)
        if v not in self.type_to_node:
            self.add_node(v)
        self.type_to_node[u].children.setdefault(tag, []).append(self.type_to_node[v])

    def add_type_recursive(self, parent: type, nested_child: type, tag: str, visited):
        if (parent, nested_child) in visited:
            return
        visited.add((parent, nested_child))
        self.add_edge_and_nodes(parent, nested_child, tag)
        t: type = nested_child
        args = get_args(t)
        if is_union(t):
            for arg in args:
                self.add_type_recursive(nested_child, arg, "v", visited)

        elif is_optional(t):
            for arg in args:
                self.add_type_recursive(nested_child, arg, "v", visited)

        elif is_dict(t):
            assert len(args) == 2
            self.add_type_recursive(nested_child, args[0], "k", visited)
            self.add_type_recursive(nested_child, args[1], "v", visited)

        elif is_list(t):
            assert len(args) == 1
            self.add_type_recursive(nested_child, args[0], "v", visited)

        elif is_set(t):
            assert len(args) == 1
            self.add_type_recursive(nested_child, args[0], "v", visited)

        elif is_game_object(t):
            mapping = t.get_mapping()
            type_hints = t.get_type_hints_cached()

            for python_name in mapping.keys():
                type_hint = type_hints[python_name]
                self.add_type_recursive(nested_child, type_hint, python_name, visited)
        else:
            # Its a simple type
            assert get_origin(t) is None, f"{t} is not a simple type as assumed"

class JsonParser:

    _PRIMITIVES = frozenset({int, float, str, bool, type(None)})
    _TYPE_QUE = deque([])

    def __init__(self):
        self.type_graph = TypeGraph()

    @classmethod
    def register_type(cls, _type):
        cls._TYPE_QUE.append(_type)

    def build_tree(self):
        visited = set()
        while self._TYPE_QUE:
            _type = self._TYPE_QUE.pop()
            self.type_graph.add_node(_type)
            mapping = _type.get_mapping()
            type_hints = _type.get_type_hints_cached()

            for python_name in mapping.keys():
                t = type_hints[python_name]
                self.type_graph.add_type_recursive(_type, t, python_name,visited)







