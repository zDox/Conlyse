import logging
from copy import deepcopy
from dataclasses import dataclass
from time import time

from conflict_interface.data_types.custom_types import HashSet
from conflict_interface.data_types.custom_types import HashSetMap
from conflict_interface.data_types.map_state.map_state_enums import TerrainType
from conflict_interface.data_types.map_state.province import Province
from conflict_interface.data_types.map_state.sea_province import SeaProvince
from conflict_interface.interface.hub_interface import HubInterface
from conflict_interface.interface.replay_interface import ReplayInterface
from conflict_interface.logger_config import setup_library_logger
from conflict_interface.replay.replay import Replay
from conflict_interface.utils.helper import safe_issubclass
from examples.helper_functions import load_credentials


@dataclass
class B:
    foo: int
if __name__ == "__main__":
    setup_library_logger(logging.DEBUG)
    username, password, email, proxy_url = load_credentials()
    locations = HashSetMap[int, Province]
    game = ReplayInterface("replay.db")
    game.open()
    game.close()
    print(game.replay.conn)
    game.replay.conn = None
    province_a = game.game_state.states
    province_b = deepcopy(game.game_state.states)
    province_b.map_state.map.provinces[9345839] = province_a.map_state.map.provinces[1]
    t1 = time()
    rp = province_a.make_replay_patch(province_b)
    print(f"Replay Patch took  {time() - t1} seconds" )
    # rp.debug_str()
    for op in rp.operations:
        print(op.path, op.new_value)