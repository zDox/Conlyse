import logging
from dataclasses import dataclass
from pprint import pprint

from conflict_interface.data_types.custom_types import ArrayList
from conflict_interface.data_types.map_state.impact import Impact
from conflict_interface.data_types.map_state.map_state_enums import ImpactType
from conflict_interface.data_types.point import Point
from conflict_interface.logger_config import setup_library_logger
from conflict_interface.replay.make_bipatch_between_gamestates import make_replay_patch


@dataclass
class B:
    foo: int
if __name__ == "__main__":
    setup_library_logger(logging.DEBUG)
    logging.basicConfig(level=logging.DEBUG)


    patches = make_replay_patch(ArrayList([Impact(pos=Point(1, 2),
                                       time=1,
                                       type=ImpactType.SEA,
                                       count=1)]),
                                ArrayList([Impact(pos=Point(1, 3),
                                       time=1,
                                       type=ImpactType.SEA,
                                       count=1)
                                ]))
    pprint(patches.operations)
