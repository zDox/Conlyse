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
    test_files = ["full_test_data_7.json", "full_test_data_8.json"]


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

    def

    def test_load_json(self):
        gitf = GameInterface()
        r = Replay("replay.db", 'r')
        r.open()
        start = r._start_time
        patch_timestamps = r.get_timestamps()
        for i, game_state_timestamp in enumerate(r.get_game_state_timestamps()):
            if i == 0:
                continue
            with self.subTest(from_timestamp=r.get_game_state_timestamps()[i-1], to_timestamp=game_state_timestamp):
                g1 = parse_game_object(GameState, r._get_game_state(r.get_game_state_timestamps()[i-1]), GameInterface())
                g2 = parse_game_object(GameState, r._get_game_state(game_state_timestamp), GameInterface())
                replay_patches = r._jump_from_to(patch_timestamps[i-1], game_state_timestamp)
                for rp in replay_patches:
                    apply_patch_any(rp, GameState, g1, GameInterface())
                json_patch = JsonPatch.from_diff(dump_any(g2), dump_any(g1))
                self.assertEqual(len(json_patch.to_string()), 2, msg=f"Failed at jump from {patch_timestamps[i-1]} to {game_state_timestamp} with {json_patch.to_string()}")