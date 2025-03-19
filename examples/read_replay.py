import json
import logging
from copy import deepcopy
from dataclasses import dataclass
from datetime import UTC
from datetime import datetime
from time import time
from deepdiff import DeepDiff

from conflict_interface.data_types.army_state.army_state import ArmyState
from conflict_interface.data_types.custom_types import DateTimeMillisecondsInt
from conflict_interface.data_types.custom_types import HashSet
from conflict_interface.data_types.custom_types import HashSetMap
from conflict_interface.data_types.game_object import dump_any
from conflict_interface.data_types.game_object import parse_game_object
from conflict_interface.data_types.game_state.game_state import GameState
from conflict_interface.data_types.map_state.map_state_enums import TerrainType
from conflict_interface.data_types.map_state.province import Province
from conflict_interface.data_types.map_state.sea_province import SeaProvince
from conflict_interface.data_types.mod_state.mod_state import ModState
from conflict_interface.data_types.player_state.player_state import PlayerState
from conflict_interface.data_types.research_state.reserach import Research
from conflict_interface.interface.game_interface import GameInterface
from conflict_interface.interface.hub_interface import HubInterface
from conflict_interface.interface.replay_interface import ReplayInterface
from conflict_interface.logger_config import setup_library_logger
from conflict_interface.replay.apply_replay import apply_patch_any
from conflict_interface.replay.apply_replay import make_replay_patch
from conflict_interface.replay.replay import Replay
from conflict_interface.utils.helper import safe_issubclass
from examples.helper_functions import load_credentials


@dataclass
class B:
    foo: int
if __name__ == "__main__":
    setup_library_logger(logging.DEBUG)
    gitf = GameInterface()
    file1 = "../tests/full_test_data_7.json"
    file2 = "../tests/full_test_data_8.json"
    state = ArmyState
    with open(file1, "r", encoding="utf-8") as f:
        data1 = json.load(f)
    with open(file2, "r", encoding="utf-8") as f:
        data2 = json.load(f)

    state1 = data1["result"]["states"][str(state.STATE_TYPE)]
    state2 = data2["result"]["states"][str(state.STATE_TYPE)]

    parsed_state1 = parse_game_object(state, state1, gitf)
    parsed_state2 = parse_game_object(state, state2, gitf)

    rp = make_replay_patch(parsed_state1, parsed_state2)
    rp.debug_str()
    print(parsed_state1 == parsed_state2)
    dumped1 = dump_any(parsed_state1)
    dumped2 = dump_any(parsed_state2)
    diff = DeepDiff(dumped1, dumped2)
    print(diff)
    apply_patch_any(rp, state, parsed_state1, GameInterface())
    print(parsed_state1 == parsed_state2)
    dumped1 = dump_any(parsed_state1)
    dumped2 = dump_any(parsed_state2)
    diff = DeepDiff(dumped1, dumped2)
    print(diff)