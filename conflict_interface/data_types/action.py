from conflict_interface.game_object.game_object import GameObject
from conflict_interface.game_object.game_object_binary import SerializationCategory
from conflict_interface.game_object.decorators import binary_serializable


from conflict_interface.data_types.version import VERSION
@binary_serializable(SerializationCategory.DATACLASS, version = VERSION)
class Action(GameObject):
    language: str = "en"
    action_request_id: str = ""

    MAPPING = {
        "language": "language",
        "action_request_id": "requestID"
    }