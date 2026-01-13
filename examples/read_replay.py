import datetime
import logging
from time import perf_counter

from conflict_interface.interface.replay_interface import ReplayInterface
from conflict_interface.logger_config import setup_library_logger
from conflict_interface.replay.constants import INT_TO_OP
from conflict_interface.replay.patch_graph import PatchGraph
from paths import TEST_DATA

if __name__ == "__main__":
    setup_library_logger(logging.DEBUG)
    logging.basicConfig(level=logging.DEBUG)

    ritf = ReplayInterface(TEST_DATA / "test_replay.bin", game_id= 12345, player_id=1)

    for i in range(10000000):
        pass
    t1 = perf_counter()
    ritf.open(mode = 'r', max_patches=None)
    ritf.register_game_info_state_trigger()

    t2 = perf_counter()
    # Test Operations --------------------------------
    # End --------------------------------------------
    t3 = perf_counter()
    ritf.close()
    t4 = perf_counter()
    print(f"Opening took  {t2 - t1:.2f} seconds")
    print(f"Opts took {t3 - t2:.2f} seconds")
    print(f"Closing took  {t4 - t3:.2f} seconds")
    print(f"Together took  {t4 - t1:.2f} seconds")
    print(f"Opening and closing took {(t2-t1+t4-t3):.2f} seconds")
