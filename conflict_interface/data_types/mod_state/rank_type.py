from dataclasses import dataclass

from conflict_interface.data_types.game_object import GameObject


@dataclass
class RankType(GameObject):
    C = "ultshared.modding.types.UltRankType"
    item_id: int
    officer: bool
    min_points: int

    MAPPING = {
        "item_id": "itemID",
        "officer": "officer",
        "min_points": "minPoints",
    }