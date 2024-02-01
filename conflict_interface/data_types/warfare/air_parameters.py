from datetime import datetime
from conflict_interface.utils import JsonMappedClass, 


@dataclass
class AirParameters(JsonMappedClass):
    last_air_action_time: datetime
    last_air_position: Position
    launch_target: Position
    max_flight_time: datetime
    air_field: Position | int  # Can be either a province_id or a Position

    mapping = {
        "last_air_action_time": MappedValue("lastAirActionTime",
                                            unixtimestamp_to_datetime),
        "last_air_position": "lastAirPosition",
        "launch_target": "launchTarget",
        "max_flight_time": MappedValue("maxFlightTime",
                                       unixtimestamp_to_datetime),
        "air_field": MappedValue("airField", parse_air_field),
    }
