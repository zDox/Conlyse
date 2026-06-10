import logging
from pathlib import Path
from pprint import pprint
from time import perf_counter

from conflict_interface.interface.replay_interface import ReplayInterface
from conflict_interface.logger_config import setup_library_logger
from paths import TEST_DATA

if __name__ == "__main__":
    setup_library_logger(logging.DEBUG)
    logging.basicConfig(level=logging.DEBUG)

    ritf = ReplayInterface("/home/zdox/PycharmProjects/Conlyse/replays_out/game_10626254.conrp", {"5652_28": TEST_DATA / Path("5652_28.bin")})


    t1 = perf_counter()
    ritf.open(mode = 'r')
    t2 = perf_counter()
    # Test Operations --------------------------------
    ritf.jump_to(ritf.last_time)
    pprint(ritf.get_())
    # End --------------------------------------------
    t3 = perf_counter()
    ritf.close()
    t4 = perf_counter()
    print(f"Opening took  {t2 - t1:.2f} seconds")
    print(f"Opts took {t3 - t2:.2f} seconds")
    print(f"Closing took  {t4 - t3:.2f} seconds")
    print(f"Together took  {t4 - t1:.2f} seconds")
    print(f"Opening and closing took {(t2-t1+t4-t3):.2f} seconds")
