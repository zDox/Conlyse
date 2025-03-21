import json
import logging
from copy import deepcopy
from dataclasses import dataclass
from datetime import UTC
from datetime import datetime
from time import time

from deepdiff import DeepDiff

from conflict_interface.data_types.army_state.army_state import ArmyState
from conflict_interface.data_types.game_object import dump_any
from conflict_interface.data_types.game_object import parse_game_object
from conflict_interface.data_types.game_state.game_state import GameState
from conflict_interface.interface.game_interface import GameInterface
from conflict_interface.interface.replay_interface import ReplayInterface
from conflict_interface.logger_config import setup_library_logger
from conflict_interface.replay.apply_replay import apply_patch_any
from conflict_interface.replay.apply_replay import make_replay_patch
from conflict_interface.replay.replay import Replay


@dataclass
class B:
    foo: int
if __name__ == "__main__":
    setup_library_logger(logging.DEBUG)
    gitf = GameInterface()
    ritf = ReplayInterface("replay.db")
    ritf.open()
    t1 = time()
    for time_stamp_int in ritf.replay.get_timestamps():
        time_stamp = datetime.fromtimestamp(time_stamp_int / 1000, tz=UTC)
        print(ritf.get_provinces_by_name("Libreville"))
        ritf.set_client_time(time_stamp)
    print(f"Jumping forward took {(time() - t1):.6f} seconds")

    timestamps = ritf.replay.get_timestamps()
    timestamps.reverse()
    t2 = time()
    for time_stamp_int in timestamps:
        time_stamp = datetime.fromtimestamp(time_stamp_int / 1000, tz=UTC)
        print(ritf.get_provinces_by_name("Libreville"))
        ritf.set_client_time(time_stamp)

    print(f"Jumping backward took {(time() - t2):.6f} seconds")