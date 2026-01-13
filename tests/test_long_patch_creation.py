from datetime import datetime, timezone
import unittest

import deepdiff
from deepdiff import DeepDiff

from conflict_interface.data_types.game_object_json import dump_any
from conflict_interface.interface.replay_interface import ReplayInterface
from conflict_interface.replay.replay import Replay
from paths import TEST_DATA
from tests.helper_functions import compare_dicts


class TestLongPatchCreation(unittest.TestCase):

    def test_long_patch_equivalence(self):
        ritf = ReplayInterface(TEST_DATA / "test_replay.bin", player_id=1, game_id=12345)
        ritf.open('r')
        ritf.jump_to(ritf.start_time)
        target_time = ritf.last_time
        ritf.jump_to(target_time)
        state_original = dump_any(ritf.game_state)

        # Get optimized state
        ritf.jump_to(ritf.start_time)
        patches = [ritf.create_and_save_long_patch(ritf.start_time, target_time)]
        ritf._apply_patches_and_update_state(patches, target_time)
        state_optimized = dump_any(ritf.game_state)

        self.assertTrue(compare_dicts(state_original, state_optimized))
        diff = DeepDiff(state_original, state_optimized)
        self.assertEqual(diff, {})
