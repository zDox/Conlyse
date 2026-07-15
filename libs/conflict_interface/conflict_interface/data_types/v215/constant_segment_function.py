from dataclasses import dataclass

from .custom_types import TreeMap
from conflict_interface.game_object.game_object import GameObject
from conflict_interface.game_object.game_object_binary import SerializationCategory
from conflict_interface.game_object.decorators import conflict_serializable


from .version import VERSION
@conflict_serializable(SerializationCategory.DATACLASS, version = VERSION)
@dataclass
class ConstantSegmentFunction(GameObject):
    C = "ultshared.modding.configuration.UltConstantSegmentsFunction"

    segment_values: TreeMap[float, float]

    MAPPING = {
        "segment_values": "segmentValues"
    }