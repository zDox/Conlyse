from datetime import datetime
from dataclasses import dataclass
from typing import Optional

from conflict_interface.utils import Point, \
        unixtimestamp_to_datetime, ConMapping
from conflict_interface.utils import GameObject

def parse_air_field(obj):
    if obj is None:
        return None
    elif "x" in obj:
        return Point.from_dict(obj)
    else:
        return int(obj[1:])
    """
    elif obj.get("@c") == "ultshared.warfare.UltTemporaryAirfield":
        return Position.from_dict(obj["airfieldPosition"])
    """


@dataclass
class AirParameters(GameObject):
    last_air_action_time: datetime
    last_air_position: Optional[Point]
    launch_target: Optional[Point]
    max_flight_time: datetime
    air_field: Optional[Point | str]  # Can be either a province_id or a Position

    MAPPING = {
        "last_air_action_time": "lastAirActionTime",
        "last_air_position": "lastAirPosition",
        "launch_target": "launchTarget",
        "max_flight_time": "maxFlightTime",
        "air_field": "airField",
    }
