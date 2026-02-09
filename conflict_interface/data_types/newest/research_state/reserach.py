from dataclasses import dataclass

from conflict_interface.data_types.custom_types import DateTimeMillisecondsInt
from conflict_interface.game_object.game_object import GameObject
from conflict_interface.game_object.game_object_binary import SerializationCategory
from conflict_interface.game_object.decorators import conflict_serializable


from conflict_interface.data_types.version import VERSION
@conflict_serializable(SerializationCategory.DATACLASS, version = VERSION)
@dataclass
class Research(GameObject):
    C = "ultshared.research.UltResearch"
    research_type_id: int
    start_time: DateTimeMillisecondsInt
    end_time: DateTimeMillisecondsInt
    speed_up: int

    MAPPING = {"research_type_id": "researchTypeID",
                "start_time": "startTime",
                "end_time": "endTime",
                "speed_up": "speedUp",
}
