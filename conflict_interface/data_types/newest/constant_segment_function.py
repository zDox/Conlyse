from dataclasses import dataclass

from conflict_interface.data_types.custom_types import TreeMap
from conflict_interface.game_object.game_object import GameObject
from conflict_interface.game_object.game_object_binary import SerializationCategory
from conflict_interface.game_object.decorators import binary_serializable


from conflict_interface.data_types.version import VERSION
@binary_serializable(SerializationCategory.DATACLASS, version = VERSION)
@dataclass
class ConstantSegmentFunction(GameObject):
    C = "ultshared.modding.configuration.UltConstantSegmentsFunction"

    segment_values: TreeMap[float, float]

    MAPPING = {
        "segment_values": "segmentValues"
    }