from conflict_interface.data_types.game_object_binary import GameObjectSerializer
from conflict_interface.data_types.game_object_binary import SerializationCategory
from conflict_interface.data_types.type_graph import TypeGraph


def binary_serializable(category: SerializationCategory):
    def wrapper(cls):
        GameObjectSerializer.register(cls, category)
        if category in (SerializationCategory.DATACLASS, SerializationCategory.POINT):
            TypeGraph.register_type(cls)
        return cls

    return wrapper
