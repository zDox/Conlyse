import logging

from build.lib.conflict_interface.utils.helper import datetime_to_unix_ms
from conflict_interface.interface.replay_interface import ReplayInterface
from conflict_interface.logger_config import setup_library_logger

if __name__ == "__main__":
    setup_library_logger(logging.DEBUG)
    logging.basicConfig(level=logging.DEBUG)

    ritf = ReplayInterface("benchmark_replay_206.db")

    ritf.open()
    def province_owner_changed(change_type, path, old_value, new_value):
        print(f"Province changed! Change type: {change_type}, Path: {path}, Old Value: {old_value}, New Value: {new_value}")

    ritf.on_province_attribute_change(province_owner_changed, "owner_id")
    current_tstamp = ritf.start_time
    next_tstamp = ritf.get_next_timestamp()
    while next_tstamp is not None:
        ritf.jump_to(next_tstamp)
        current_tstamp = next_tstamp
        next_tstamp = ritf.get_next_timestamp()
    ritf.close()