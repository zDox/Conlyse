import logging
from time import perf_counter

from conflict_interface.interface.replay_interface import ReplayInterface
from conflict_interface.logger_config import setup_library_logger
from paths import TEST_DATA

if __name__ == "__main__":
    setup_library_logger(logging.DEBUG)
    logging.basicConfig(level=logging.DEBUG)

    ritf = ReplayInterface(TEST_DATA / "test_replay10k.bin", mode='r', player_id=1, game_id=12345)
    t1 = perf_counter()
    ritf.open()
    t2 = perf_counter()
    # --------------------------------------------------
    # Needed for rw mode:
    ritf.jump_to(ritf.replay.get_last_time())
    ritf.replay.set_last_game_state(ritf.game_state)
    # --------------------------------------------------
    t3 = perf_counter()
    ritf.close()
    t4 = perf_counter()
    print(f"Opening took  {t2 - t1:.2f} seconds")
    print(f"Opts tooks {t3 - t2:.2f} seconds")
    print(f"Closing took  {t4 - t3:.2f} seconds")
    print(f"Together took  {t4 - t1:.2f} seconds")
    print(f"Opening and closing took {(t2-t1+t4-t3):.2f} seconds")