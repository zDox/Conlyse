from conflict_interface.data_types.game_object import GameObject
from conflict_interface.data_types.game_object_binary import SerializationCategory
from conflict_interface.data_types.game_object_binary import binary_serializable


@binary_serializable(SerializationCategory.DATACLASS)
class Action(GameObject):
    language = "en"
    action_request_id = ""

    MAPPING = {
        "language": "language",
        "action_request_id": "requestID"
    }