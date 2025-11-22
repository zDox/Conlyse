
from pathlib import Path

from conflict_interface.replay.make_bipatch_between_gamestates import make_bireplay_patch
from conflict_interface.replay.replay import Replay
from conflict_interface.utils.helper import unix_ms_to_datetime
from tools.recording_converter.recorder_logger import get_logger
from tools.recording_converter.recording_reader import RecordingReader

logger = get_logger()
class FromGameStateUsingMakeBiPatchToReplay:
    def __init__(self, recording_reader: RecordingReader):
        self.reader = recording_reader
        self.game_states_file = self.reader.game_states_file

    def convert(self,
                output_file: str,
                overwrite: bool = False,
                game_id: int = None,
                player_id: int = None) -> bool:
        """
        Convert using game state-based approach (make_bireplay_patch on consecutive states).

        Args:
            output_file: Path to the output replay database file
            overwrite: Whether to overwrite existing output file
            game_id: Game ID (extracted from first state if not provided)
            player_id: Player ID (extracted from first state if not provided)

        Returns:
            bool: True if successful, False otherwise
        """
        len_game_states = self.reader.len_game_states()

        if len_game_states == 0:
            logger.error("No game_states loaded. Can not convert to Replay using states")
            return False

        # Extract game_id and player_id from first state if not provided
        first_timestamp_ms, first_state = self.reader.read_game_state(0)

        if game_id is None:
            logger.error("Could not determine game_id from recording")
            return False

        if player_id is None:
            logger.error("Could not determine player_id from recording")
            return False

        logger.info(f"Converting recording to replay using state-based mode: game_id={game_id}, player_id={player_id}")
        logger.info(f"Total game states: {len_game_states}")
        output_path = Path(output_file)
        if output_path.exists() and overwrite:
            # delete existing file
            logger.info(f"Overwriting existing output file: {output_file}")
            output_path.unlink()

        # Create replay in write mode
        with Replay(file_path=output_file, mode='w', game_id=game_id, player_id=player_id) as replay:
            # Record initial game state
            first_datetime = unix_ms_to_datetime(first_timestamp_ms)
            logger.info(f"Recording initial state at {first_datetime}")
            replay.record_initial_game_state(
                time_stamp=first_datetime,
                game_id=game_id,
                player_id=player_id,
                game_state=first_state
            )

            # Record static map data if available
            static_map_data = self.reader.read_static_map_data()
            if not static_map_data:
                logger.error("No static map data found in recording")
                return False

            logger.info("Recording static map data")
            replay.record_static_map_data(
                static_map_data=static_map_data,
                game_id=game_id,
                player_id=player_id
            )

            # Create patches between consecutive states
            prev_state = first_state

            for i in range(1, len_game_states):
                logger.info(f"Creating patch {i}/{len_game_states - 1} at {current_datetime}")

                timestamp_ms, current_state = self.reader.read_game_state(i)
                current_datetime = unix_ms_to_datetime(timestamp_ms)

                # Create bidirectional patch
                bipatch = make_bireplay_patch(prev_state, current_state)

                # Record the patch
                replay.record_bipatch(
                    time_stamp=current_datetime,
                    game_id=game_id,
                    player_id=player_id,
                    replay_patch=bipatch
                )

                prev_state = current_state

        logger.info(f"Successfully converted recording to replay: {output_file}")
        return True