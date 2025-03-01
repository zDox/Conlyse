from dataclasses import dataclass

from conflict_interface.data_types.custom_types import TreeMap


@dataclass
class ConstantSegmentFunction:
    C = "ultshared.modding.configuration.UltConstantSegmentsFunction"

    segment_values: TreeMap[float, float]

    MAPPING = {
        "segment_values": "segmentValues"
    }