from pathlib import Path

from tqdm import tqdm

from conflict_interface.data_types.game_object import GameObject
from conflict_interface.data_types.game_object import parse_any
from conflict_interface.data_types.game_state.game_state import GameState
from conflict_interface.interface.game_interface import GameInterface
from conflict_interface.replay.make_bipatch_between_gamestates import make_bireplay_patch
from conflict_interface.replay.replay import Replay
from conflict_interface.replay.replay_patch import BidirectionalReplayPatch
from conflict_interface.utils.helper import unix_ms_to_datetime
from tools.recording_converter.recorder_logger import get_logger
from tools.recording_converter.recording_reader import RecordingReader

logger = get_logger()

class FromJsonResponsesUsingUpdateToReplay:
    def __init__(self, recoding_reader: RecordingReader):
        self.reader = recoding_reader

    def convert(self, output_file: Path, overwrite: bool = False, limit: int = None, game_id: int = None, player_id: int = None) -> bool:
        """
        Convert using JSON-based approach (parse JSON responses and apply updates).

        Uses the GameState.update() method to create patches, which allows for more
        accurate tracking of state changes compared to comparing final states.

        Args:
            output_file: Path to the output replay database file
            overwrite: Whether to overwrite existing output file
            limit: Maximum number of JSON responses to process
            game_id: Game ID (extracted from first state if not provided)
            player_id: Player ID (extracted from first state if not provided)

        Returns:
            bool: True if successful, False otherwise
        """
        # Read JSON responses
        logger.info("Reading JSON responses from recording")
        json_responses = self.reader.read_json_responses(limit)
        if not json_responses:
            logger.error("No JSON responses found in recording")
            return False

        # Extract game_id and player_id
        if game_id is None:
            logger.error("Could not determine game_id from recording")
            return False

        if player_id is None:
            logger.error("Could not determine player_id from recording, using 0")
            return False

        logger.info(f"Converting recording to replay using JSON-based mode: game_id={game_id}, player_id={player_id}")
        logger.info(f"Processing {len(json_responses)} JSON responses")

        # Create a mock game interface for parsing context
        mock_game = GameInterface()
        initial_game_state_written = False

        output_path = Path(output_file)
        if output_path.exists() and overwrite:
            # delete existing file
            logger.info(f"Overwriting existing output file: {output_file}")
            output_path.unlink()
        elif output_path.exists() and not overwrite:
            logger.error(f"Output file already exists: {output_file}")
            return False

        # Create replay in write mode
        if limit:
            max_patches = limit * 4
        else:
            max_patches = len(json_responses) * 4
        with Replay(file_path=output_file, mode='w', game_id=game_id, player_id=player_id, max_patches=max_patches) as replay:
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
            game_activation_count = 0
            # Process JSON responses and create patches using update method
            for i in tqdm(range(len(json_responses)), desc="Writing Replay: ", unit="Patch", unit_scale=True):
                _, json_response = json_responses[i] # timestamp_ms is the real timestamp of the response

                try:
                    if json_response.get("action") == "UltActivateGameAction":
                        game_activation_count += 1
                        logger.debug(f"Skipping response {i} as it is an UltActivateGameAction")
                        if game_activation_count > 2:
                            logger.error(f"More then 2 UltActivateGameActions!!!")
                        continue
                    new_state: GameState = parse_any(GameState, json_response["result"], mock_game)
                    current_timestamp = unix_ms_to_datetime(int(new_state.time_stamp))
                    # Parse JSON response into new state
                    if json_response["result"]["@c"] == "ultshared.UltGameState" and not initial_game_state_written:
                        # Record initial game state
                        logger.info(f"Recording initial state at {current_timestamp} game time")
                        replay.record_initial_game_state(
                            time_stamp=current_timestamp,
                            game_id=game_id,
                            player_id=player_id,
                            game_state=new_state
                        )
                        current_state = new_state
                        initial_game_state_written = True
                        continue
                    elif json_response["result"]["@c"] == "ultshared.UltGameState" and initial_game_state_written:
                        # Entire new game state -> replace current state -> make_bireplay_patch
                        logger.info(f"Creating bireplay patch using make_bireplay_patch for response {i} at {current_timestamp} game time")
                        bipatch = make_bireplay_patch(current_state, new_state)
                        current_state = new_state
                    elif initial_game_state_written:
                        # Create a bidirectional replay patch object
                        bipatch = BidirectionalReplayPatch()

                        # Call update with the bipatch to record differences
                        current_state.update(new_state, path=[], rp=bipatch)
                    else:
                        logger.error("First JSON response is not a full game state")
                        return False

                    # Record the patch
                    replay.read_write_record_patch(
                        time_stamp=current_timestamp,
                        game_id=game_id,
                        player_id=player_id,
                        replay_patch=bipatch,
                        game=mock_game
                    )
                except Exception as e:
                    logger.error(f"Error processing JSON response at {current_timestamp} game time: {e}")
                    # Continue with next response
                    continue

            GameObject.set_game_recursive(current_state, None)
            replay.set_last_game_state(current_state)
        return True