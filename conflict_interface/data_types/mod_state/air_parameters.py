from dataclasses import dataclass
from typing import Optional
from typing import Union

from conflict_interface.data_types.custom_types import DateTimeMillisecondsInt
from conflict_interface.data_types.game_object import GameObject
from conflict_interface.data_types.point import Point

@dataclass
class TemporaryAirfield(GameObject):
    C = "ultshared.warfare.UltTemporaryAirfield"

    air_field_position: Point

    MAPPING = {
        "air_field_position": "airfieldPosition",
    }


@dataclass
class AirParameters(GameObject):
    C = "ap"
    last_air_action_time: DateTimeMillisecondsInt
    last_air_position: Optional[Point]
    launch_target: Optional[Point]
    max_flight_time: Optional[DateTimeMillisecondsInt]
    air_field: Optional[Union[str, TemporaryAirfield]]  # Can be either a province_id or a Position

    MAPPING = {
        "last_air_action_time": "lastAirActionTime",
        "last_air_position": "lastAirPosition",
        "launch_target": "launchTarget",
        "max_flight_time": "maxFlightTime",
        "air_field": "airField",
    }
    def get_airfield_position(self) -> Point | None:
        if not self.air_field:
            return None
        if isinstance(self.air_field, TemporaryAirfield):
            return self.air_field.air_field_position
        else:
            province_id = self.air_field.removeprefix("p")
            return self.game.get_province(int(province_id)).static_data.center_coordinate
