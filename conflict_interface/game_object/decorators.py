from conflict_interface.game_object.game_object_binary import GameObjectSerializer
from conflict_interface.game_object.game_object_binary import SerializationCategory
from conflict_interface.game_object.type_graph import TypeGraph


def binary_serializable(category: SerializationCategory, version: int ):
    def wrapper(cls):
        GameObjectSerializer.register(version, cls, category)
        if category in (SerializationCategory.DATACLASS, SerializationCategory.POINT):
            TypeGraph.register_type(version, cls)
        return cls

    return wrapper
