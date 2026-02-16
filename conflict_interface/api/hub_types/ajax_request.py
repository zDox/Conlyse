from dataclasses import dataclass
from typing import get_type_hints

from conflict_interface.game_object.game_object_binary import SerializationCategory
from conflict_interface.game_object.decorators import conflict_serializable


from ..version import VERSION
@conflict_serializable(SerializationCategory.DATACLASS, version = VERSION)
@dataclass
class AjaxRequest:
    name: str
    host: str
    callback_obj_name: str
    action: str
    language_id: int
    keys: list
    values: list
    buffer_request: bool = False
    is_polling: bool = False
    evaluate_response: bool = False
    current_request: int = 0
    method = "post"

    MAPPING = {}
    _type_hints = None

    @classmethod
    def get_type_hints_cached(cls):
        if cls._type_hints is None:
            cls._type_hints = get_type_hints(cls)
        return cls._type_hints