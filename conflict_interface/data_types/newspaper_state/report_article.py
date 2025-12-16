from dataclasses import dataclass

from conflict_interface.data_types.game_object import GameObject
from conflict_interface.data_types.game_object_binary import SerializationCategory
from conflict_interface.data_types.game_object_binary import binary_serializable


@binary_serializable(SerializationCategory.DATACLASS)
@dataclass
class ReportArticle(GameObject):
    C = "ultshared.UltReportArticle"

    state_id: int

    MAPPING = {
        "state_id": "stateID"
    }