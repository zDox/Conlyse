import json
import unittest
from datetime import UTC

from deepdiff import DeepDiff
from jsonpatch import JsonPatch

from conflict_interface.data_types.army_state.army_state import ArmyState
from conflict_interface.data_types.custom_types import DateTimeMillisecondsInt
from conflict_interface.data_types.custom_types import HashMap
from conflict_interface.data_types.foreign_affairs_state.foreign_affairs_state import ForeignAffairRelations
from conflict_interface.data_types.foreign_affairs_state.foreign_affairs_state import ForeignAffairsState
from conflict_interface.data_types.foreign_affairs_state.foreign_affairs_state_enums import ForeignAffairRelationTypes
from conflict_interface.data_types.game_event_state.game_event_state import GameEventState
from conflict_interface.data_types.game_info_state.game_info_state import GameInfoState
from conflict_interface.data_types.game_object import dump_any
from conflict_interface.data_types.game_object import parse_game_object
from conflict_interface.data_types.game_state.game_state import GameState
from conflict_interface.data_types.map_state.map_state import MapState
from conflict_interface.data_types.mod_state.mod_state import ModState
from conflict_interface.data_types.newspaper_state.newspaper_state import NewspaperState
from conflict_interface.data_types.player_state.player_state import PlayerState
from conflict_interface.data_types.research_state.research_state import ResearchState
from conflict_interface.data_types.research_state.reserach import Research
from conflict_interface.data_types.resource_state.resource_state import ResourceState
from conflict_interface.interface.game_interface import GameInterface
from conflict_interface.interface.hub_interface import HubInterface
from conflict_interface.replay.apply_replay import apply_patch_any
from conflict_interface.replay.apply_replay import make_replay_patch
from conflict_interface.replay.replay import Replay
from conflict_interface.replay.replay_patch import AddOperation
from conflict_interface.replay.replay_patch import PathNode
from conflict_interface.replay.replay_patch import RemoveOperation
from conflict_interface.replay.replay_patch import ReplaceOperation
from conflict_interface.replay.replay_patch import ReplayPatch
from conflict_interface.utils.exceptions import AuthenticationException
from tests.compare_dicts import compare_dicts
from tests.helper_functions import get_new_game_id
from tests.helper_functions import load_credentials

random_prefix = "test_"


class ReplayPatchTest(unittest.TestCase):
    test_states = [ModState, ResourceState, MapState, NewspaperState, PlayerState, ArmyState, ForeignAffairsState,
                   ResearchState, GameInfoState, GameEventState]


    def test_to_string_simple(self):
        # AddOperation
        rp = ReplayPatch()
        rp.add_op(["test"], 2)
        self.assertEqual(rp.to_string(), '[["a", ["test"], 2]]')

        # ReplaceOperation
        rp = ReplayPatch()
        rp.replace_op(["test"], 2)
        self.assertEqual(rp.to_string(), '[["p", ["test"], 2]]')

        # RemoveOperation
        rp = ReplayPatch()
        rp.remove_op(["test"])
        self.assertEqual(rp.to_string(), '[["r", ["test"], null]]')


    def test_from_string_simple(self):
        # AddOperation
        rp = ReplayPatch()
        rp.add_op(["test"], 2)
        self.assertEqual(rp.operations, ReplayPatch.from_string('[["a", ["test"], 2]]').operations)

        # ReplaceOperation
        rp = ReplayPatch()
        rp.replace_op(["test"], 2)
        self.assertEqual(rp.operations, ReplayPatch.from_string('[["p", ["test"], 2]]').operations)

        # RemoveOperation
        rp = ReplayPatch()
        rp.remove_op(["test"])
        self.assertEqual(rp.operations, ReplayPatch.from_string('[["r", ["test"], null]]').operations)
