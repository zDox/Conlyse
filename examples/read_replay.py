import json
import logging
from copy import deepcopy
from dataclasses import dataclass
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from pprint import pprint
from time import sleep
from time import time
from typing import Optional
from typing import Union
from typing import get_args


from conflict_interface.data_types.army_state.army import Army
from conflict_interface.data_types.army_state.army_state import ArmyState
from conflict_interface.data_types.custom_types import ArrayList
from conflict_interface.data_types.custom_types import EmptyList
from conflict_interface.data_types.custom_types import HashMap
from conflict_interface.data_types.custom_types import LinkedList
from conflict_interface.data_types.foreign_affairs_state.foreign_affairs_state_enums import ForeignAffairRelationTypes
from conflict_interface.data_types.game_object import dump_any
from conflict_interface.data_types.game_object import get_inner_type
from conflict_interface.data_types.game_object import parse_game_object
from conflict_interface.data_types.game_state.game_state import GameState
from conflict_interface.data_types.map_state.province_property import ProvinceProperty
from conflict_interface.data_types.mod_state.moddable_upgrade import ModableUpgrade
from conflict_interface.data_types.resource_state.resource_state_enums import ResourceType
from conflict_interface.interface.game_interface import GameInterface
from conflict_interface.interface.replay_interface import ReplayInterface
from conflict_interface.logger_config import setup_library_logger
from conflict_interface.replay.apply_replay import apply_patch_any
from conflict_interface.replay.apply_replay import get_list_element_type
from conflict_interface.replay.apply_replay import make_replay_patch
from conflict_interface.replay.apply_replay import recur_path
from conflict_interface.replay.replay import Replay


@dataclass
class B:
    foo: int
if __name__ == "__main__":
    setup_library_logger(logging.DEBUG)
    logging.basicConfig(level=logging.DEBUG)

    print(get_list_element_type(Optional[HashMap[int, ProvinceProperty]], {'@c': 'ultshared.UltProvinceProperties'}))
    a: dict[ResourceType, str] = {ResourceType.NONE: "100"}
    print(a[ResourceType(0)])



    gitf = GameInterface()
    ritf = ReplayInterface("replay.db")

    ritf.open()
    t1 = time()
    amount_patches = len(ritf.get_timestamps())
    ritf.set_client_time(ritf.end_time)
    t2 = time()
    print(f"Setting time took {t2 - t1} seconds for {amount_patches} patches. {(t2 - t1) / amount_patches} patches per second")
    ritf.close()

