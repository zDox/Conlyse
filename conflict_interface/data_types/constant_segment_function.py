from dataclasses import dataclass

from conflict_interface.data_types.custom_types import TreeMap
from conflict_interface.data_types.game_object import GameObject
from conflict_interface.data_types.game_object_binary import SerializationCategory
from conflict_interface.data_types.decorators import binary_serializable


@binary_serializable(SerializationCategory.DATACLASS)
@dataclass
class ConstantSegmentFunction(GameObject):
    C = "ultshared.modding.configuration.UltConstantSegmentsFunction"

    segment_values: TreeMap[float, float]

    MAPPING = {
        "segment_values": "segmentValues"
    }