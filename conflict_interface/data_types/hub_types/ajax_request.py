from dataclasses import dataclass

from conflict_interface.data_types.game_object_binary import SerializationCategory
from conflict_interface.data_types.game_object_binary import binary_serializable


@binary_serializable(SerializationCategory.DATACLASS)
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