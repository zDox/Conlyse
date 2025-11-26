from copy import deepcopy
from logging import getLogger
from pathlib import Path

from tqdm import tqdm

from conflict_interface.data_types.game_object import dump_any
from conflict_interface.data_types.game_object import parse_any
from conflict_interface.data_types.game_state.game_state import GameState
from conflict_interface.interface.game_interface import GameInterface
from conflict_interface.interface.replay_interface import ReplayInterface
from conflict_interface.replay.constants import ADD_OPERATION
from conflict_interface.replay.constants import REMOVE_OPERATION
from conflict_interface.replay.constants import REPLACE_OPERATION
from conflict_interface.utils.helper import unix_ms_to_datetime
from paths import TEST_DATA
from tests.helper_functions import compare_dicts
from tools.recording_converter.converter import RecordingConverter
from tools.recording_converter.enums import OperatingMode
from tools.recording_converter.recording_reader import RecordingReader

logger = getLogger()

class ReplayRoundtrip:
    def __init__(self, recording_file_path: Path = TEST_DATA / "test_recording", replay_file_path: Path = TEST_DATA / "test_replay.bin", preconverted = False):
        self.recording_file_path: Path = recording_file_path
        self.replay_file_path: Path = replay_file_path
        self.player_id = 85
        self.current_time = None
        self.last_time = None
        self.limit = 100
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
            output=TEST_DATA / "test_replay.bin",
            overwrite=True,
            game_id=12345,  # optional
            player_id=self.player_id, # optional
            limit = self.limit
        )

        assert success

    def run(self):
        reader = RecordingReader(self.recording_file_path)
        ritf = ReplayInterface(self.replay_file_path)
        ritf.open()
        ritf.replay.storage.path_tree.validate_tree_structure()

        mock_game = GameInterface()

        initial_game_state_written = False

        json_responses = reader.read_json_responses(self.limit)
        self.current_time = ritf.replay.get_start_time()

        for i in tqdm(range(len(json_responses)), desc="Comparing Game States", unit="State", unit_scale=True):
            timestamp_ms, json_response = json_responses[i]


            if json_response.get("action") == "UltActivateGameAction":
                #logger.warning(f"Skipping response {i} as it is an UltActivateGameAction")
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

            logger.debug(f"Started Error Analysis")
            print(f"Error occoured betweeen {self.last_time} and {self.current_time} at i = {i}")

            ritf.jump_to(self.last_time)
            replay_state_before = deepcopy(ritf.game_state)
            ritf.jump_to(self.current_time)
            replay_state_now = ritf.game_state

            tree = ritf.replay.storage.path_tree
            tree.validate_tree_structure()

            if len(applied_patches) == 0:
                print()
                logger.error("No patches applied")

            elif len(applied_patches) == 1:
                print()
                print("One Patch Applied")
                patch = applied_patches[0]
                for i, (op_type, path, value) in enumerate(zip(patch.op_types, patch.paths, patch.values)):
                    if op_type == ADD_OPERATION:
                        print(f"{i} ADD: {tree.get_old_path_for_debug(path)}, New Value is : {str(value)[:100]}")
                    elif op_type == REPLACE_OPERATION:
                        print(f"{i} REPLACE: {tree.get_old_path_for_debug(path)}, with : {str(value)[:100]}")
                    elif op_type == REMOVE_OPERATION:
                        print(f"{i} REMOVE: {tree.get_old_path_for_debug(path)}")

            else:
                print()
                print("=" * 60)
                logger.warning("More then One Patch Applied")
                print("More then One Patch Applied")
                print("="*60)
                print()
                print()
                for i in range(len(applied_patches)):
                    patch = applied_patches[i]
                    from_ts = patch.from_timestamp
                    to_ts = patch.to_timestamp

                    print(f"Applying Patch from {from_ts} to {to_ts}")
                    for i, (op_type, path, value) in enumerate(zip(patch.op_types, patch.paths, patch.values)):
                        if op_type == ADD_OPERATION:
                            print(f"{i} ADD: {tree.get_old_path_for_debug(path)}, New Value is : {str(value)[:100]}")
                        elif op_type == REPLACE_OPERATION:
                            print(f"{i} REPLACE: {tree.get_old_path_for_debug(path)}, with : {str(value)[:100]}")
                        elif op_type == REMOVE_OPERATION:
                            print(f"{i} REMOVE: {tree.get_old_path_for_debug(path)}")

            print("Errors Concluded")
            return False


    def compare_game_states(self, game_is, game_should):
        # Debug: Working stats:
        json_is = dump_any(game_is.states.game_event_state)
        json_should = dump_any(game_should.states.game_event_state)
        success = compare_dicts(json_should, json_is)
        return success




if __name__ == "__main__":
    r = ReplayRoundtrip()
    r.run()