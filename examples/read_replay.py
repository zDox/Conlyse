import logging
from time import perf_counter

from conflict_interface.interface.game_interface import GameInterface
from conflict_interface.interface.replay_interface import ReplayInterface
from conflict_interface.logger_config import setup_library_logger

if __name__ == "__main__":
    setup_library_logger(logging.DEBUG)
    logging.basicConfig(level=logging.DEBUG)
    gitf = GameInterface()
    t1 = perf_counter()
    ritf = ReplayInterface("../tools/recording_converter/rec01.db")

    ritf.open()
    t2 = perf_counter()
    time_stamps_ = ritf.get_timestamps()
    time_stamps = len(time_stamps_)
    amount_patches = len(time_stamps_)
    for timestamp in ritf.get_timestamps():
        ritf.jump_to_next_patch()

    t3 = perf_counter()
    print(len(ritf.get_armies()))
    print(ritf.replay.storage.path_tree.get_old_path_for_debug(230))
    print(f"Setting time took {t3 - t2} seconds for {amount_patches} patches. {(t3 - t2) / amount_patches * 1e6} microseconds per patch.")
    print(f"Loading took {t2 - t1} seconds.")
    ritf.replay.debug_print()
    ritf.close()