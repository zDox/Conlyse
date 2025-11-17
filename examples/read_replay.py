import logging
import pickle
from dataclasses import dataclass
from pprint import pprint
from time import time

import zstandard as zstd

from conflict_interface.interface.game_interface import GameInterface
from conflict_interface.interface.replay_interface import ReplayInterface


@dataclass
class B:
    foo: int
if __name__ == "__main__":
    #setup_library_logger(logging.DEBUG)
    #logging.basicConfig(level=logging.DEBUG)

    gitf = GameInterface()
    t1 = time()
    ritf = ReplayInterface("test_replay3.db")

    ritf.open()
    t2 = time()
    time_stamps = len(ritf.get_timestamps())
    amount_patches = len(ritf.get_timestamps())
    for timestamp in ritf.get_timestamps():
        ritf.set_client_time(timestamp)
    t3 = time()
    print(list(ritf.get_map().provinces.values())[0].name)
    print(f"Setting time took {t3 - t2} seconds for {amount_patches} patches. {(t3 - t2) / amount_patches} seconds per patch.")
    print(f"Loading took {t2 - t1} seconds.")
    ritf.close()