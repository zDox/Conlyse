from dataclasses import dataclass

from conflict_interface.game_object.game_object import GameObject
from conflict_interface.game_object.game_object_binary import SerializationCategory
from conflict_interface.game_object.decorators import binary_serializable
from conflict_interface.data_types.update_helpers import universal_update
from conflict_interface.replay.replay_patch import BidirectionalReplayPatch
from conflict_interface.replay.constants import PathNode


@binary_serializable(SerializationCategory.DATACLASS)
@dataclass
class RankingEntry(GameObject):
    C = "ultshared.UltRankingEntry"
    id: int
    type: str
    points: int
    percentage: float

    MAPPING = {
        "id": "id",
        "type": "type",
        "points": "points",
        "percentage": "percentage",
    }

    def update(self, other: "RankingEntry", path: list[PathNode] = None, rp: BidirectionalReplayPatch = None):
        return universal_update(self, other, path, rp)