
from pathlib import Path

from tqdm import tqdm

from conflict_interface.replay.make_bipatch_between_gamestates import make_bireplay_patch
from conflict_interface.replay.replay_segment import ReplaySegment
from conflict_interface.utils.helper import unix_ms_to_datetime
from recorder_logger import get_logger
from recording_reader import RecordingReader

logger = get_logger()
class FromGameStateUsingMakeBiPatchToReplay:
    def __init__(self, recording_reader: RecordingReader, use_tqdm: bool = True):
        self.reader = recording_reader
        self.game_states_file = self.reader.game_states_file
        self._use_tqdm = use_tqdm

    def convert(self,
                output_file: Path,
                overwrite: bool = False,
                limit: int = None,
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
        with ReplaySegment(file_path=output_file, mode='w', game_id=game_id, player_id=player_id) as replay:
            # Record initial game state
            first_datetime = unix_ms_to_datetime(int(first_state.time_stamp))
            logger.info(f"Recording initial state at {first_datetime} game time")
            replay.record_initial_game_state(
                time_stamp=first_datetime,
                game_id=game_id,
                player_id=player_id,
                game_state=first_state
            )

            # Create patches between consecutive states
            prev_state = first_state

            number_of_states_to_process = len_game_states if limit is None else min(limit, len_game_states)

            iterator = range(1, number_of_states_to_process)
            if self._use_tqdm:
                iterator = tqdm(
                    iterator,
                    desc="Processing: ",
                    unit="States",
                    unit_scale=True,
                )

            for i in iterator:
                _, current_state = self.reader.read_game_state(i)
                current_datetime = unix_ms_to_datetime(int(current_state.time_stamp))

                # Create bidirectional patch
                bipatch = make_bireplay_patch(prev_state, current_state)

                # Record the patch
                replay.record_patch_in_rw_mode(
                    time_stamp=current_datetime,
                    game_id=game_id,
                    player_id=player_id,
                    replay_patch=bipatch,
                    game=None
                )

                prev_state = current_state

        return True

