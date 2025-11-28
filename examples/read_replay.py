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
    ritf.open()
    # Preload
    ritf.jump_to(ritf.replay.get_last_time())
    ritf.jump_to(ritf.replay.get_start_time())

    time_stamps_ = ritf.get_timestamps()
    time_stamps = len(time_stamps_)
    amount_patches = len(time_stamps_)
    times = []
    t2 = perf_counter()
    for timestamp in ritf.get_timestamps():
        patches = ritf.jump_to_next_patch()
    t3 = perf_counter()

    print(f"Setting time took {t3 - t2} seconds for {amount_patches} patches. {(t3 - t2) / amount_patches * 1e6} microseconds per patch.")
    print(f"Loading took {t2 - t1} seconds.")
    print(f"Applied Operations: {ritf.replay.get_op_counter()}")
    ritf.close()