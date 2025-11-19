import logging
import time

from conflict_interface.utils.helper import datetime_to_unix_ms
from conflict_interface.data_types.map_state.province import Province
from conflict_interface.interface.replay_interface import ReplayInterface
from conflict_interface.logger_config import setup_library_logger

if __name__ == "__main__":
    setup_library_logger(logging.DEBUG)
    logging.basicConfig(level=logging.DEBUG)

    ritf = ReplayInterface("benchmark_replay_206.db")

    ritf.open()
    ritf.replay.load_patches_from_disk_into_cache()
    def province_added(province):
        print(f"Province added! ID: {province}")
    def province_owner_changed(province: Province, old_value, new_value):
        print(f"Owner of Province {province.name}! Changed from {ritf.get_player(old_value).name} -> {ritf.get_player(new_value).name}")

    ritf.on_province_add(province_added)
    ritf.on_province_attribute_change(province_owner_changed, "owner_id")

    # Start timing
    start_time = time.time()

    current_tstamp = ritf.start_time
    next_tstamp = ritf.get_next_timestamp()
    jump_count = 0
    while next_tstamp is not None:
        try:
            ritf.jump_to_next_patch()
            jump_count += 1
            current_tstamp = next_tstamp
            next_tstamp = ritf.get_next_timestamp()
        except Exception:
            print(f"Failed to jump to {next_tstamp}/{datetime_to_unix_ms(ritf.current_time)}")
            ritf.current_time = next_tstamp
            ritf.current_timestamp_index += 1
            current_tstamp = next_tstamp
            next_tstamp = ritf.get_next_timestamp()

    # End timing
    end_time = time.time()
    elapsed_time = end_time - start_time

    print(f"\n{'='*60}")
    print(f"Replay skip completed!")
    print(f"Total time: {elapsed_time:.2f} seconds ({elapsed_time/60:.2f} minutes)")
    print(f"Total jumps: {jump_count}")
    print(f"Average time per jump: {elapsed_time/jump_count*1000:.2f} ms" if jump_count > 0 else "No jumps performed")
    print(f"{'='*60}")

    ritf.close()