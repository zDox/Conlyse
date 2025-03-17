import logging
from copy import deepcopy
from dataclasses import dataclass
from time import time

from conflict_interface.data_types.custom_types import HashSet
from conflict_interface.data_types.map_state.province import Province
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
    locations = HashSet[Province]
    game = ReplayInterface("replay.db")
    game.open()
    game.close()
    print(game.replay.conn)
    game.replay.conn = None
    province_a = game.game_state.states.map_state.map
    province_b = deepcopy(game.game_state.states.map_state.map)
    province_b.locations[1].morale = 21
    province_b.morale = 29
    rp = province_a.record(province_b)
    print(issubclass(type(province_a.locations).__origin__, list))
