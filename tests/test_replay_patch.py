import json
import unittest
from datetime import UTC

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
    test_files = ["full_test_data_4.json", "full_test_data_5.json"]

    def test_simple_patch(self):
       t1 = Research(research_type_id=2,
                     start_time=DateTimeMillisecondsInt(2024, 8, 1, tzinfo=UTC),
                     end_time=DateTimeMillisecondsInt(2024, 8, 1, tzinfo=UTC),
                     speed_up=1)

       t2 = Research(research_type_id=1,
                     start_time=DateTimeMillisecondsInt(2024, 8, 1, tzinfo=UTC),
                     end_time=DateTimeMillisecondsInt(2024, 8, 1, tzinfo=UTC),
                     speed_up=1)
       rp = make_replay_patch(t1, t2)
       self.assertEqual(rp.operations, [ReplaceOperation(["research_type_id"], 1)])
       apply_patch_any(rp, Research, t1, None)
       self.assertEqual(t1, t2)

    def test_simple_multiple_patch(self):
        t1 = Research(research_type_id=1,
                      start_time=DateTimeMillisecondsInt(2024, 8, 1, tzinfo=UTC),
                      end_time=DateTimeMillisecondsInt(2024, 8, 1, tzinfo=UTC),
                      speed_up=1)

        t2 = Research(research_type_id=2,
                      start_time=DateTimeMillisecondsInt(2024, 8, 2, tzinfo=UTC),
                      end_time=DateTimeMillisecondsInt(2024, 8, 2, tzinfo=UTC),
                      speed_up=2)
        rp = make_replay_patch(t1, t2)
        self.assertEqual(rp.operations, [
            ReplaceOperation(["research_type_id"], 2),
            ReplaceOperation(["start_time"], 1722556800000),
            ReplaceOperation(["end_time"], 1722556800000),
            ReplaceOperation(["speed_up"], 2),
        ],
                                                )
        apply_patch_any(rp, Research, t1, None)
        self.assertEqual(t1, t2)

    def test_dict_replace_patch(self):
        t1 = ForeignAffairRelations(
            state_id=1,
            players=1,
            end_of_honor_period=HashMap({
                1: DateTimeMillisecondsInt(2024, 8, 1, tzinfo=UTC),
            }),
            neighbor_relations={},
        )
        t2 = ForeignAffairRelations(
            state_id=1,
            players=1,
            end_of_honor_period=HashMap({
                1: DateTimeMillisecondsInt(2024, 8, 2, tzinfo=UTC),
            }),
            neighbor_relations={},
        )
        rp = make_replay_patch(t1, t2)
        self.assertEqual(rp.operations, [
            ReplaceOperation(["end_of_honor_period", 1], 1722556800000),
        ])
        apply_patch_any(rp, ForeignAffairRelations, t1, None)
        self.assertEqual(t1, t2)

    def test_dict_add_patch(self):
        t1 = ForeignAffairRelations(
            state_id=1,
            players=1,
            end_of_honor_period=HashMap({
                1: DateTimeMillisecondsInt(2024, 8, 1, tzinfo=UTC),
            }),
            neighbor_relations={},
        )
        t2 = ForeignAffairRelations(
            state_id=1,
            players=1,
            end_of_honor_period=HashMap({
                1: DateTimeMillisecondsInt(2024, 8, 2, tzinfo=UTC),
                2: DateTimeMillisecondsInt(2024, 8, 3, tzinfo=UTC),
            }),
            neighbor_relations={},
        )
        rp = make_replay_patch(t1, t2)
        self.assertEqual(rp.operations, [
            ReplaceOperation(["end_of_honor_period", 1], 1722556800000),
            AddOperation(path=['end_of_honor_period', 2], new_value=1722643200000)
        ])
        apply_patch_any(rp, ForeignAffairRelations, t1, None)
        self.assertEqual(t1, t2)

    def test_dict_remove_patch(self):
        t1 = ForeignAffairRelations(
            state_id=1,
            players=1,
            end_of_honor_period=HashMap({
                1: DateTimeMillisecondsInt(2024, 8, 1, tzinfo=UTC),
                2: DateTimeMillisecondsInt(2024, 8, 3, tzinfo=UTC),
            }),
            neighbor_relations={},
        )
        t2 = ForeignAffairRelations(
            state_id=1,
            players=1,
            end_of_honor_period=HashMap({
                1: DateTimeMillisecondsInt(2024, 8, 2, tzinfo=UTC),
            }),
            neighbor_relations={},
        )
        rp = make_replay_patch(t1, t2)
        self.assertEqual(rp.operations, [
            ReplaceOperation(["end_of_honor_period", 1], 1722556800000),
            RemoveOperation(path=['end_of_honor_period', 2])
        ])
        apply_patch_any(rp, ForeignAffairRelations, t1, None)
        self.assertEqual(t1, t2)

    def test_multidimensional_dict_replace_patch(self):
        t1 = ForeignAffairRelations(
            state_id=1,
            players=1,
            end_of_honor_period=HashMap({}),
            neighbor_relations={
                1: {
                    2: ForeignAffairRelationTypes.PEACE,
                }
            },
        )
        t2 = ForeignAffairRelations(
            state_id=1,
            players=1,
            end_of_honor_period=HashMap({}),
            neighbor_relations={
                1: {
                    2: ForeignAffairRelationTypes.WAR,
                }
            },
        )
        rp = make_replay_patch(t1, t2)
        self.assertEqual(rp.operations, [
            ReplaceOperation(path=['neighbor_relations', 1, 2], new_value=-2)
        ])
        apply_patch_any(rp, ForeignAffairRelations, t1, None)
        self.assertEqual(t1, t2)

    def test_multidimensional_dict_add_patch(self):
        t1 = ForeignAffairRelations(
            state_id=1,
            players=1,
            end_of_honor_period=HashMap({}),
            neighbor_relations={
                1: {
                    2: ForeignAffairRelationTypes.PEACE,
                }
            },
        )
        t2 = ForeignAffairRelations(
            state_id=1,
            players=1,
            end_of_honor_period=HashMap({}),
            neighbor_relations={
                1: {
                    2: ForeignAffairRelationTypes.PEACE,
                    3: ForeignAffairRelationTypes.PEACE,
                },
                2: {
                    2: ForeignAffairRelationTypes.PEACE,
                }
            },
        )
        rp = make_replay_patch(t1, t2)
        self.assertEqual(rp.operations, [
            AddOperation(path=['neighbor_relations', 1, 3], new_value=1),
            AddOperation(path=['neighbor_relations', 2], new_value={'2': 1})
        ])
        apply_patch_any(rp, ForeignAffairRelations, t1, None)
        self.assertEqual(t1, t2)


    def test_to_string_simple(self):
        # AddOperation
        rp = ReplayPatch()
        rp.add_op(AddOperation(["test"], 2))
        self.assertEqual(rp.to_string(), '[["a", ["test"], 2]]')

        # ReplaceOperation
        rp = ReplayPatch()
        rp.replace_op(ReplaceOperation(["test"], 2))
        self.assertEqual(rp.to_string(), '[["p", ["test"], 2]]')

        # RemoveOperation
        rp = ReplayPatch()
        rp.remove_op(RemoveOperation(["test"]))
        self.assertEqual(rp.to_string(), '[["r", ["test"], null]]')


    def test_from_string_simple(self):
        # AddOperation
        rp = ReplayPatch()
        rp.add_op(AddOperation(["test"], 2))
        self.assertEqual(rp.operations, ReplayPatch.from_string('[["a", ["test"], 2]]').operations)

        # ReplaceOperation
        rp = ReplayPatch()
        rp.replace_op(ReplaceOperation(["test"], 2))
        self.assertEqual(rp.operations, ReplayPatch.from_string('[["p", ["test"], 2]]').operations)

        # RemoveOperation
        rp = ReplayPatch()
        rp.remove_op(RemoveOperation(["test"]))
        self.assertEqual(rp.operations, ReplayPatch.from_string('[["r", ["test"], null]]').operations)


    def test_load_json(self):

        for file in self.test_files:
            with self.subTest(file=file):
                # Read in the json file
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                self.assertLess(2, len(data["result"]["states"])) # just tests if loading the file throws an error


    def test_convert_states(self):
        for file in self.test_files:
            with self.subTest(file = file):
                # Read in the json file
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                rp = ReplayPatch()

                states = data["result"]
                parsed_state = parse_game_object(GameState, states, GameInterface())
                self.assertIsInstance(parsed_state, GameState) # Just checks if parsing throws an error


    def test_make_apply_replay_patch_states(self):
        for file1 in self.test_files:
            with open(file1, "r", encoding="utf-8") as f:
                data1 = json.load(f)
            for file2 in self.test_files:
                with open(file2, "r", encoding="utf-8") as f:
                    data2 = json.load(f)
                for state in self.test_states:
                    if file1 == file2:
                        continue
                    with self.subTest(file1=file1, file2=file2, state = state):
                        gitf = GameInterface()
                        state1 = data1["result"]["states"][str(state.STATE_TYPE)]
                        state2 = data2["result"]["states"][str(state.STATE_TYPE)]

                        parsed_state1 = parse_game_object(state, state1, gitf)
                        parsed_state2 = parse_game_object(state, state2, gitf)

                        rp = make_replay_patch(parsed_state1, parsed_state2)

                        apply_patch_any(rp, state, parsed_state2, gitf)


                        errors = compare_dicts(state2, json.dump(dump_any(parsed_state2)))
                        self.assertTrue(errors, msg=f"Failed for {state}")