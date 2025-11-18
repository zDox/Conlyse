import logging
import pickle
from dataclasses import dataclass
from pprint import pprint
from time import time

import zstandard as zstd

from conflict_interface.interface.game_interface import GameInterface
from conflict_interface.interface.replay_interface import ReplayInterface
from conflict_interface.logger_config import setup_library_logger


@dataclass
class B:
    foo: int
if __name__ == "__main__":
    setup_library_logger(logging.DEBUG)
    logging.basicConfig(level=logging.DEBUG)

    gitf = GameInterface()
    t1 = time()
    ritf = ReplayInterface("benchmark_replay_206.db")

    ritf.open()
    t2 = time()
    time_stamps = len(ritf.get_timestamps())
    amount_patches = len(ritf.get_timestamps())
    for timestamp in ritf.get_timestamps():
        try:
            ritf.jump_to(timestamp)
        except Exception:
            print(f"Failed to jump to {timestamp}/{datetime_to_unix_ms(ritf.current_time)}")
    t3 = time()
    print(f"Setting time took {t3 - t2} seconds for {amount_patches} patches. {(t3 - t2) / amount_patches} seconds per patch.")
    print(f"Loading took {t2 - t1} seconds.")
    ritf.close()