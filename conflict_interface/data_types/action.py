from conflict_interface.data_types.game_object import GameObject
from conflict_interface.data_types.game_object_binary import SerializationCategory
from conflict_interface.data_types.decorators import binary_serializable


@binary_serializable(SerializationCategory.DATACLASS)
class Action(GameObject):
    language: str = "en"
    action_request_id: str = ""

    MAPPING = {
        "language": "language",
        "action_request_id": "requestID"
    }