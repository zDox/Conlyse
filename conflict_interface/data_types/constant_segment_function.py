from dataclasses import dataclass

from conflict_interface.data_types.custom_types import TreeMap
from conflict_interface.data_types.game_object import GameObject


@dataclass
class ConstantSegmentFunction(GameObject):
    C = "ultshared.modding.configuration.UltConstantSegmentsFunction"

    segment_values: TreeMap[float, float]

    MAPPING = {
        "segment_values": "segmentValues"
    }