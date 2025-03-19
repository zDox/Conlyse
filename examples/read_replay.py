import json
import logging
from copy import deepcopy
from dataclasses import dataclass

from deepdiff import DeepDiff

from conflict_interface.data_types.army_state.army_state import ArmyState
from conflict_interface.data_types.game_object import dump_any
from conflict_interface.data_types.game_object import parse_game_object
from conflict_interface.data_types.game_state.game_state import GameState
from conflict_interface.interface.game_interface import GameInterface
from conflict_interface.logger_config import setup_library_logger
from conflict_interface.replay.apply_replay import apply_patch_any
from conflict_interface.replay.apply_replay import make_replay_patch
from conflict_interface.replay.replay import Replay


@dataclass
class B:
    foo: int
if __name__ == "__main__":
    setup_library_logger(logging.DEBUG)
    gitf = GameInterface()
    r = Replay("replay.db", 'r')
    r.open()
    g1 = parse_game_object(GameState, r._get_game_state(1742422847653), GameInterface())
    g2 = parse_game_object(GameState, r._get_game_state(1742422850371), GameInterface())
    rp = r._get_patch(1742422850371, 1742422851238)
    apply_patch_any(rp, GameState, g1, GameInterface())
    print(dump_any(g1))
    diff = DeepDiff(dump_any(g1), dump_any(g2))
    # print(diff)