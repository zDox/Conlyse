from dataclasses import dataclass

from conflict_interface.data_types.game_object import GameObject


@dataclass
class ReportArticle(GameObject):
    C = "ultshared.UltReportArticle"

    state_id: int

    MAPPING = {
        "state_id": "stateID"
    }