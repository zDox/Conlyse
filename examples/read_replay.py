import logging
from time import perf_counter

from conflict_interface.interface.replay_interface import ReplayInterface
from conflict_interface.logger_config import setup_library_logger
from paths import TEST_DATA

if __name__ == "__main__":
    setup_library_logger(logging.DEBUG)
    logging.basicConfig(level=logging.DEBUG)
    t1 = perf_counter()
    ritf = ReplayInterface(TEST_DATA / "test_replay10k.bin")
    t2 = perf_counter()
    ritf.open()
    t3 = perf_counter()
    print(f"Opening took  {t3 - t2:.2f} seconds")
    ritf.close()