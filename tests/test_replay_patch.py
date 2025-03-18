import unittest
from datetime import UTC

from conflict_interface.data_types.custom_types import DateTimeMillisecondsInt
from conflict_interface.data_types.custom_types import HashMap
from conflict_interface.data_types.foreign_affairs_state.foreign_affairs_state import ForeignAffairRelations
from conflict_interface.data_types.foreign_affairs_state.foreign_affairs_state_enums import ForeignAffairRelationTypes
from conflict_interface.data_types.research_state.reserach import Research
from conflict_interface.interface.hub_interface import HubInterface
from conflict_interface.replay.apply_replay import apply_patch_any
from conflict_interface.replay.replay_patch import AddOperation
from conflict_interface.replay.replay_patch import RemoveOperation
from conflict_interface.replay.replay_patch import ReplaceOperation
from conflict_interface.utils.exceptions import AuthenticationException
from tests.helper_functions import get_new_game_id
from tests.helper_functions import load_credentials

random_prefix = "test_"

class ReplayPatch(unittest.TestCase):
    def test_simple_patch(self):
       r1 = Research(research_type_id=2,
                     start_time=DateTimeMillisecondsInt(2024, 8, 1, tzinfo=UTC),
                     end_time=DateTimeMillisecondsInt(2024, 8, 1, tzinfo=UTC),
                     speed_up=1)

       r2 = Research(research_type_id=1,
                     start_time=DateTimeMillisecondsInt(2024, 8, 1, tzinfo=UTC),
                     end_time=DateTimeMillisecondsInt(2024, 8, 1, tzinfo=UTC),
                     speed_up=1)
       rp = r1.make_replay_patch(r2)
       self.assertEqual(rp.operations, [ReplaceOperation(["research_type_id"], 1)])
       apply_patch_any(rp, Research, r1, None)
       self.assertEqual(r1, r2)

    def test_simple_multiple_patch(self):
        r1 = Research(research_type_id=1,
                      start_time=DateTimeMillisecondsInt(2024, 8, 1, tzinfo=UTC),
                      end_time=DateTimeMillisecondsInt(2024, 8, 1, tzinfo=UTC),
                      speed_up=1)

        r2 = Research(research_type_id=2,
                      start_time=DateTimeMillisecondsInt(2024, 8, 2, tzinfo=UTC),
                      end_time=DateTimeMillisecondsInt(2024, 8, 2, tzinfo=UTC),
                      speed_up=2)
        rp = r1.make_replay_patch(r2)
        self.assertEqual(rp.operations, [
            ReplaceOperation(["research_type_id"], 2),
            ReplaceOperation(["start_time"], 1722556800000),
            ReplaceOperation(["end_time"], 1722556800000),
            ReplaceOperation(["speed_up"], 2),
        ],
                                                )
        apply_patch_any(rp, Research, r1, None)
        self.assertEqual(r1, r2)

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
        rp = t1.make_replay_patch(t2)
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
        rp = t1.make_replay_patch(t2)
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
        rp = t1.make_replay_patch(t2)
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
        rp = t1.make_replay_patch(t2)
        self.assertEqual(rp.operations, [
            ReplaceOperation(["end_of_honor_period", 1], 1722556800000),
            RemoveOperation(path=['end_of_honor_period', 2])
        ])
        apply_patch_any(rp, ForeignAffairRelations, t1, None)
        self.assertEqual(t1, t2)