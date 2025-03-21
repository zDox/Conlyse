import unittest

from conflict_interface.data_types.army_state.army_state import ArmyState
from conflict_interface.data_types.foreign_affairs_state.foreign_affairs_state import ForeignAffairsState
from conflict_interface.data_types.game_event_state.game_event_state import GameEventState
from conflict_interface.data_types.game_info_state.game_info_state import GameInfoState
from conflict_interface.data_types.map_state.map_state import MapState
from conflict_interface.data_types.mod_state.mod_state import ModState
from conflict_interface.data_types.newspaper_state.newspaper_state import NewspaperState
from conflict_interface.data_types.player_state.player_state import PlayerState
from conflict_interface.data_types.research_state.research_state import ResearchState
from conflict_interface.data_types.resource_state.resource_state import ResourceState
from conflict_interface.replay.replay_patch import ReplayPatch

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
