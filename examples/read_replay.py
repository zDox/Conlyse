import logging
from copy import deepcopy
from dataclasses import dataclass
from datetime import UTC
from datetime import datetime
from time import time
from deepdiff import DeepDiff

from conflict_interface.data_types.custom_types import DateTimeMillisecondsInt
from conflict_interface.data_types.custom_types import HashSet
from conflict_interface.data_types.custom_types import HashSetMap
from conflict_interface.data_types.game_object import dump_any
from conflict_interface.data_types.game_state.game_state import GameState
from conflict_interface.data_types.map_state.map_state_enums import TerrainType
from conflict_interface.data_types.map_state.province import Province
from conflict_interface.data_types.map_state.sea_province import SeaProvince
from conflict_interface.data_types.research_state.reserach import Research
from conflict_interface.interface.hub_interface import HubInterface
from conflict_interface.interface.replay_interface import ReplayInterface
from conflict_interface.logger_config import setup_library_logger
from conflict_interface.replay.apply_replay import apply_patch_any
from conflict_interface.replay.replay import Replay
from conflict_interface.utils.helper import safe_issubclass
from examples.helper_functions import load_credentials


@dataclass
class B:
    foo: int
if __name__ == "__main__":
    setup_library_logger(logging.DEBUG)
    username, password, email, proxy_url = load_credentials()

    r1 = Research(research_type_id=2,
                  start_time=DateTimeMillisecondsInt.now(),
                  end_time=DateTimeMillisecondsInt.now(),
                  speed_up=1)

    r2 = Research(research_type_id=1,
                  start_time=DateTimeMillisecondsInt.now(),
                  end_time=DateTimeMillisecondsInt.now(),
                  speed_up=1)
    rp = r1.make_replay_patch(r2)
    rp.debug_str()
    apply_patch_any(rp, Research, r1, None)
    print(r1)