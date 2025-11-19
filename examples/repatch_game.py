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

from conflict_interface.data_types.army_state.army_state import ArmyState
from conflict_interface.data_types.game_object import dump_any
from conflict_interface.data_types.game_object import parse_game_object
from conflict_interface.data_types.game_state.game_state import GameState
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
    gitf = GameInterface()
    r = Replay("replay2.db", "a")
    time_stamps = r.get_game_state_timestamps()
    for current_timestamp, next_timestamp in zip(time_stamps, time_stamps[1:]):
        pass
