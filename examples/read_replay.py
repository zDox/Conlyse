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
    # logging.basicConfig(level=logging.DEBUG)





    gitf = GameInterface()
    t1 = time()
    ritf = ReplayInterface("test_replay1.db")

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

    # Zstandard compressor (reusable for better performance)
    _compressor = zstd.ZstdCompressor(level=3)  # Level 3 is good balance
    _decompressor = zstd.ZstdDecompressor()
    compression = True
    with open("test.pickle", "wb") as f:
        t_static = time()
        ritf.game_state.set_game(None)
        ritf.game_state.states.map_state.map.static_map_data.set_game(None)
        pprint(ritf.game_state.states.map_state.map.static_map_data.game)
        f.write(
            _compressor.compress(
                pickle.dumps(ritf.game_state)
            ) if compression else pickle.dumps(ritf.game_state)
        )
        print(f"Pickling static map data took {time() - t_static} seconds.")

    with open("test.pickle", "rb") as f:
        t_static = time()
        if compression:
            game_state = pickle.loads(_decompressor.decompress(f.read()))
        else:
            game_state = pickle.load(f)
        game_state.set_game(ritf)
        game_state.states.map_state.map.static_map_data.set_game(ritf)
        print(f"Unpickling static map data took {time() - t_static} seconds.")

    ritf.close()