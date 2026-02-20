from conflict_interface.game_object.game_object_binary import GameObjectSerializer
from conflict_interface.game_object.game_object_binary import SerializationCategory
from conflict_interface.game_object.game_object_parse_json import JsonParser
from conflict_interface.game_object.type_graph import TypeGraph


def conflict_serializable(category: SerializationCategory, version: int):
    def wrapper(cls):
        #print(f"Registering serialization cls {cls} in category {category}, version: {version}")
        GameObjectSerializer.register(version, cls, category)
        if category in (SerializationCategory.DATACLASS, SerializationCategory.POINT):
            TypeGraph.register_type(version, cls)
        if category == SerializationCategory.STATIC_MAP_DATA:
            JsonParser.register_static_map_data(version, cls)
        if category == SerializationCategory.GAME_STATE:
            JsonParser.register_game_state(version, cls)
        return cls

    return wrapper


def parse_edge_case(tag: str, version: int):
    #print(f"Registering Edge Case {tag} version {version}")
    def wrapper(cls):
        JsonParser.register_edge_case(tag, version, cls)
        return cls
    return wrapper

