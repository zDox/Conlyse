import logging
from copy import deepcopy
from logging import getLogger
from pathlib import Path

from deepdiff import DeepDiff
from tqdm import tqdm

from conflict_interface.data_types.game_object import dump_any
from conflict_interface.data_types.game_object import parse_any
from conflict_interface.data_types.game_state.game_state import GameState
from conflict_interface.interface.game_interface import GameInterface
from conflict_interface.interface.replay_interface import ReplayInterface
from conflict_interface.logger_config import setup_library_logger
from conflict_interface.replay.constants import ADD_OPERATION
from conflict_interface.replay.constants import REMOVE_OPERATION
from conflict_interface.replay.constants import REPLACE_OPERATION
from conflict_interface.utils.helper import unix_ms_to_datetime
from paths import TEST_DATA
from tools.recording_converter.converter import RecordingConverter
from tools.recording_converter.enums import OperatingMode
from tools.recording_converter.recording_reader import RecordingReader

logger = getLogger()


class ReplayRoundtrip:
    def __init__(self, recording_file_path: Path = TEST_DATA / "test004",
                 replay_file_path: Path = TEST_DATA / "test_replay004.bin", preconverted=False):
        self.recording_file_path: Path = recording_file_path
        self.replay_file_path: Path = replay_file_path
        self.player_id = 85
        self.current_time = None
        self.last_time = None
        self.limit = 37
        self.compare_start_index = 0

        if not preconverted:
            self.start_converter()

    def start_converter(self):
        # Create converter for replay conversion (gmr mode)
        converter = RecordingConverter(
            self.recording_file_path,
            OperatingMode.rur
        )

        # Convert to replay
        success = converter.convert(
            output=self.replay_file_path,
            overwrite=True,
            game_id=12345,  # optional
            player_id=self.player_id,  # optional
            limit=self.limit
        )

        assert success

    def run(self):
        reader = RecordingReader(self.recording_file_path)
        ritf = ReplayInterface(self.replay_file_path)
        ritf.open(mode = 'r')
        ritf._replay.storage.path_tree.validate_tree_structure()

        mock_game = GameInterface()

        initial_game_state_written = False

        json_responses = reader.read_json_responses(self.limit)
        self.current_time = ritf._replay.get_start_time()

        for i in tqdm(range(len(json_responses)), desc="Comparing Game States", unit="State", unit_scale=True):
            timestamp_ms, json_response = json_responses[i]

            if json_response.get("action") == "UltActivateGameAction":
                # logger.warning(f"Skipping response {i} as it is an UltActivateGameAction")
                continue

            new_state: GameState = parse_any(GameState, json_response["result"], mock_game)
            self.last_time = self.current_time
            self.current_time = unix_ms_to_datetime(int(new_state.time_stamp))
            # Parse JSON response into new state
            if json_response["result"]["@c"] == "ultshared.UltGameState" and not initial_game_state_written:
                recorder_state = new_state
                initial_game_state_written = True
                continue
            elif json_response["result"]["@c"] == "ultshared.UltGameState" and initial_game_state_written:
                # Entire new game state -> replace current state

                recorder_state = new_state

            elif initial_game_state_written:
                recorder_state.update(new_state, [])

            else:
                logger.error("JSON response is not a full game state")
                return False

            if i < self.compare_start_index: continue
            applied_patches = ritf.jump_to(self.current_time)
            replay_state = ritf.game_state
            success = self.compare_game_states(replay_state, recorder_state)
            if success: continue

            # Error occurred - begin analysis
            logger.error("\n\n")
            logger.error("Started Error Analysis")
            logger.error(f"Error occurred between {self.last_time} and {self.current_time} at i = {i}")

            ritf.jump_to(self.last_time)
            replay_state_before = deepcopy(ritf.game_state)
            ritf.jump_to(self.current_time)
            replay_state_now = ritf.game_state

            dict_replay_state = dump_any(replay_state)
            dict_recorder_state = dump_any(recorder_state)

            diff = DeepDiff(dict_replay_state, dict_recorder_state)
            print(diff)
            print(dict_replay_state['actionResults'].get('@c'))


            ritf._replay.storage.path_tree.validate_tree_structure()

            # Analyze applied patches
            if not applied_patches:
                logger.error("No patches applied")
            else:
                self._print_patches(applied_patches, ritf._replay.storage.path_tree)

            logger.error("Error analysis concluded")
            return False

    def _print_patches(self, patches, tree):
        """Print patch operations for debugging."""
        if len(patches) == 1:
            logger.error("One patch applied")
            self._print_single_patch(patches[0], tree)
        else:
            logger.error(f"{len(patches)} patches applied")
            for patch in patches:
                logger.error(f"Patch from {patch.from_timestamp} to {patch.to_timestamp}")
                self._print_single_patch(patch, tree)

    def _print_single_patch(self, patch, tree):
        """Print operations from a single patch."""
        for idx, (op_type, path, value) in enumerate(zip(patch.op_types, patch.paths, patch.values)):
            debug_path = tree.idx_to_old_path(path)

            if op_type == ADD_OPERATION:
                logger.error(f"{idx} ADD: {debug_path}, New Value: {str(value)[:100]}")
            elif op_type == REPLACE_OPERATION:
                logger.error(f"{idx} REPLACE: {debug_path}, with: {str(value)[:100]}")
            elif op_type == REMOVE_OPERATION:
                logger.error(f"{idx} REMOVE: {debug_path}")

    def compare_game_states(self, game_is: GameState, game_should: GameState):
        # Debug: Working stats:
        dict_is = dump_any(game_is)
        dict_should = dump_any(game_should)


        return dict_is == dict_should


if __name__ == "__main__":
    setup_library_logger(logging.DEBUG)
    logging.basicConfig(level=logging.DEBUG)
    r = ReplayRoundtrip()
    r.run()