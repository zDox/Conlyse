from functools import wraps

from conflict_interface.game_object.game_object_binary import GameObjectSerializer
from conflict_interface.game_object.game_object_binary import SerializationCategory
from conflict_interface.game_object.game_object_parse_json import JsonParser
from conflict_interface.game_object.type_graph import TypeGraph


def conflict_serializable(category: SerializationCategory, version: int):
    def wrapper(cls):
        GameObjectSerializer.register(version, cls, category)
        if category in (SerializationCategory.DATACLASS, SerializationCategory.POINT):
            TypeGraph.register_type(version, cls)
        return cls

    return wrapper

def custom_parser(type_: type, version: int):
    def deco(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            JsonParser.register_custom_parser(type_, version, func)
            return func(*args, **kwargs)
        return wrapper
    return deco

def parse_edge_case(tag: str, version: int):
    def wrapper(cls):
        JsonParser.register_edge_case(tag, version, cls)
        return cls
    return wrapper

