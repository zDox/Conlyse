import json
import logging
from copy import deepcopy
from dataclasses import dataclass
from datetime import UTC
from datetime import datetime
from pprint import pprint
from time import sleep
from time import time

from deepdiff import DeepDiff

from conflict_interface.utils.helper import unix_ms_to_datetime
from conflict_interface.data_types.army_state.army_state import ArmyState
from conflict_interface.data_types.custom_types import ArrayList
from conflict_interface.data_types.game_object import dump_any
from conflict_interface.data_types.game_object import parse_game_object
from conflict_interface.data_types.game_state.game_state import GameState
from conflict_interface.data_types.map_state.impact import Impact
from conflict_interface.data_types.map_state.map_state_enums import ImpactType
from conflict_interface.data_types.map_state.province import Province
from conflict_interface.data_types.point import Point
from conflict_interface.interface.game_interface import GameInterface
from conflict_interface.interface.replay_interface import ReplayInterface
from conflict_interface.logger_config import setup_library_logger
from conflict_interface.replay.apply_replay import apply_patch_any
from conflict_interface.replay.make_bireplay_patch import make_replay_patch
from conflict_interface.replay.replay import Replay


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
