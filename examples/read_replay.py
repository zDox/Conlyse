import json
import logging
from copy import deepcopy
from dataclasses import dataclass
from datetime import UTC
from datetime import datetime
from datetime import timedelta
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
from conflict_interface.replay.apply_replay import make_replay_patch
from conflict_interface.replay.replay import Replay


@dataclass
class B:
    foo: int
if __name__ == "__main__":
    setup_library_logger(logging.DEBUG)
    logging.basicConfig(level=logging.DEBUG)
    gitf = GameInterface()
    ritf = Replay("replay2.db")
    ritf.open()
    t1 = time()
    before_string = "27.03.2025 04:21:29"
    after_string = "27.03.2025 04:21:33"

    before_timestamp = datetime.fromtimestamp(datetime.strptime(before_string, "%d.%m.%Y %H:%M:%S").timestamp(), tz=UTC)
    after_timestamp = datetime.fromtimestamp(datetime.strptime(after_string, "%d.%m.%Y %H:%M:%S").timestamp(), tz=UTC)

    print(before_timestamp.tzname())
    print("Jumping forward")
    print(ritf.current_time.timestamp(), ritf.get_relation(86,35))
    ritf.set_client_time(before_timestamp)
    print(ritf.current_time.timestamp(), ritf.get_relation(86,35))
    ritf.set_client_time(after_timestamp)
    print(ritf.current_time.timestamp(), ritf.get_relation(86,35))
    ritf.set_client_time(before_timestamp - timedelta(minutes=50))
    print(ritf.current_time.timestamp(), ritf.get_relation(86,35))

    time_stamps = ritf.replay.get_timestamps()
    time_stamps.reverse()

    ritf.set_client_time(datetime.fromtimestamp(1742670897685 / 1000, tz=UTC))