from conflict_interface.data_types.game_object_binary import GameObjectSerializer
from conflict_interface.data_types.game_object_binary import SerializationCategory
from conflict_interface.data_types.game_object_parse_json import JsonParser


def binary_serializable(category: SerializationCategory):
    def wrapper(cls):
        GameObjectSerializer.register(cls, category)
        if category in (SerializationCategory.DATACLASS, SerializationCategory.POINT):
            JsonParser.register_type(cls)
        return cls

    return wrapper
