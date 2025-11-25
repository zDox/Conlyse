from logging import getLogger
from pathlib import Path

from tqdm import tqdm

from conflict_interface.data_types.game_object import dump_any
from conflict_interface.data_types.game_object import parse_any
from conflict_interface.data_types.game_state.game_state import GameState
from conflict_interface.interface.game_interface import GameInterface
from conflict_interface.interface.replay_interface import ReplayInterface
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
        self.limit = 1000

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
        ritf = ReplayInterface(self.replay_file_path)
        ritf.open()

        reader = RecordingReader( self.recording_file_path )
        mock_game = GameInterface()
        initial_game_state_written = False

        json_responses = reader.read_json_responses(self.limit)

        for i in tqdm(range(len(json_responses)), desc="Comparing Game States", unit="State", unit_scale=True):
            timestamp_ms, json_response = json_responses[i]


            if json_response.get("action") == "UltActivateGameAction":
                #logger.warning(f"Skipping response {i} as it is an UltActivateGameAction")
                continue
            new_state = parse_any(GameState, json_response["result"], mock_game)
            current_time = unix_ms_to_datetime(new_state.time_stamp)
            self.current_time = current_time
            # Parse JSON response into new state
            if json_response["result"]["@c"] == "ultshared.UltGameState" and not initial_game_state_written:
                current_state = new_state
                initial_game_state_written = True
                continue
            elif json_response["result"]["@c"] == "ultshared.UltGameState" and initial_game_state_written:
                # Entire new game state -> replace current state

                current_state = new_state

            elif initial_game_state_written:
                current_state.update(new_state, [])

            else:
                logger.error("JSON response is not a full game state")
                return False

            ritf.jump_to(current_time)
            replay_state = ritf.game_state
            self.compare_game_states(replay_state, current_state)

    def compare_game_states(self, game_is, game_should):
        # Debug: Working stats:
        json_is = dump_any(game_is.states.map_state)
        json_should = dump_any(game_should.states.map_state)
        success = compare_dicts(json_should, json_is)
        assert success, f"Comparing game states, current_time: {self.current_time}"

if __name__ == "__main__":
    r = ReplayRoundtrip()
    r.run()