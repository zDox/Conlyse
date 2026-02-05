from dataclasses import dataclass

from conflict_interface.game_object.game_object import GameObject
from conflict_interface.game_object.game_object_binary import SerializationCategory
from conflict_interface.game_object.decorators import binary_serializable


@binary_serializable(SerializationCategory.DATACLASS)
@dataclass
class ReportArticle(GameObject):
    C = "ultshared.UltReportArticle"

    state_id: int

    MAPPING = {
        "state_id": "stateID"
    }