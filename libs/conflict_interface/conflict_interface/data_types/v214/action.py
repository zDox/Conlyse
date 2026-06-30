from conflict_interface.game_object.game_object import GameObject
from conflict_interface.game_object.game_object_binary import SerializationCategory
from conflict_interface.game_object.decorators import conflict_serializable


from .version import VERSION
@conflict_serializable(SerializationCategory.DATACLASS, version = VERSION)
class Action(GameObject):
    language: str = "en"
    action_request_id: str = ""

    MAPPING = {
        "language": "language",
        "action_request_id": "requestID"
    }