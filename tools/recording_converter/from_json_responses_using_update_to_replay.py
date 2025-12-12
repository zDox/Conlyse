from pathlib import Path
from typing import Optional

from tqdm import tqdm

from conflict_interface.data_types.game_object import GameObject
from conflict_interface.data_types.game_object import parse_any
from conflict_interface.data_types.game_state.game_state import GameState
from conflict_interface.data_types.static_map_data import StaticMapData
from conflict_interface.interface.game_interface import GameInterface
from conflict_interface.replay.make_bipatch_between_gamestates import make_bireplay_patch
from conflict_interface.replay.replay import Replay
from conflict_interface.replay.replay_patch import BidirectionalReplayPatch
from conflict_interface.utils.helper import unix_ms_to_datetime
from tools.recording_converter.recorder_logger import get_logger
from tools.recording_converter.recording_reader import RecordingReader

logger = get_logger()


class FromJsonResponsesUsingUpdateToReplay:
    """
    Converts game recordings from JSON responses to replay database format.

    This converter processes JSON responses containing game state updates and creates
    bidirectional replay patches that can be used to reconstruct game states at any point.
    """

    # Constants
    GAME_ACTIVATION_ACTION = "UltActivateGameAction"
    FULL_STATE_TYPE = "ultshared.UltGameState"
    PATCH_BUFFER_MULTIPLIER = 2

    def __init__(self, recording_reader: RecordingReader):
        """
        Initialize the converter with a recording reader.

        Args:
            recording_reader: Reader instance for accessing recording data
        """
        self.reader = recording_reader

    def convert(
            self,
            output_file: Path,
            overwrite: bool = False,
            limit: Optional[int] = None,
            game_id: Optional[int] = None,
            player_id: Optional[int] = None
    ) -> bool:
        """
        Convert recording to replay database using JSON-based approach.

        This method parses JSON responses and applies state updates using GameState.update(),
        which provides accurate tracking of state changes compared to simple state comparisons.

        Args:
            output_file: Path to the output replay database file
            overwrite: Whether to overwrite existing output file
            limit: Maximum number of JSON responses to process (None for all)
            game_id: Game ID (must be provided or extraction will fail)
            player_id: Player ID (must be provided or extraction will fail)

        Returns:
            True if conversion succeeded, False otherwise
        """
        # Validate input parameters
        if not self._validate_ids(game_id, player_id):
            return False

        # Load JSON responses from recording
        json_responses = self._load_json_responses(limit)
        if json_responses is None:
            return False

        # Prepare output file
        if not self._prepare_output_file(output_file, overwrite):
            return False

        # Load static map data
        static_map_data = self._load_static_map_data()
        if static_map_data is None:
            return False

        # Calculate maximum patches for replay database
        max_patches = self._calculate_max_patches(json_responses, limit)

        # Find the initial game state index
        initial_idx = self._find_initial_game_state_index(json_responses)
        if initial_idx is None:
            return False

        # Initialize replay database and record initial state
        replay = self._initialize_replay(
            output_file, game_id, player_id, max_patches, static_map_data
        )
        if replay is None:
            return False

        # Record initial game state
        current_state = self._record_initial_state(
            replay, json_responses, initial_idx, game_id, player_id
        )
        if current_state is None:
            return False

        # Reopen replay in append mode for processing remaining states
        replay = self._reopen_replay_for_append(output_file, game_id, player_id)
        if replay is None:
            return False

        # Process all subsequent JSON responses and create patches
        success = self._process_json_responses(
            replay, json_responses, initial_idx, current_state, game_id, player_id
        )

        if success:
            # Finalize replay database
            self._finalize_replay(replay, current_state)
            logger.info(f"Successfully converted recording to replay: {output_file}")

        return success

    def _validate_ids(self, game_id: Optional[int], player_id: Optional[int]) -> bool:
        """Validate that required IDs are provided."""
        if game_id is None:
            logger.error("game_id is required but was not provided")
            return False

        if player_id is None:
            logger.error("player_id is required but was not provided")
            return False

        logger.info(f"Converting recording: game_id={game_id}, player_id={player_id}")
        return True

    def _load_json_responses(self, limit: Optional[int]) -> Optional[list]:
        """Load JSON responses from recording."""
        logger.info("Loading JSON responses from recording...")
        json_responses = self.reader.read_json_responses(limit)

        if not json_responses:
            logger.error("No JSON responses found in recording")
            return None

        logger.info(f"Loaded {len(json_responses)} JSON responses")
        return json_responses

    def _prepare_output_file(self, output_file: Path, overwrite: bool) -> bool:
        """Prepare output file, handling existing files based on overwrite flag."""
        output_path = Path(output_file)

        if output_path.exists():
            if overwrite:
                logger.info(f"Overwriting existing output file: {output_file}")
                output_path.unlink()
            else:
                logger.error(f"Output file already exists (use overwrite=True): {output_file}")
                return False

        return True

    def _load_static_map_data(self) -> StaticMapData | None:
        """Load static map data from recording."""
        logger.info("Loading static map data...")
        static_map_data = self.reader.read_static_map_data()

        if not static_map_data:
            logger.error("No static map data found in recording")
            return None

        logger.info("Static map data loaded successfully")
        return static_map_data

    def _calculate_max_patches(self, json_responses: list, limit: Optional[int]) -> int:
        """Calculate maximum number of patches needed for replay database."""
        if limit:
            max_patches = limit * self.PATCH_BUFFER_MULTIPLIER
        else:
            max_patches = len(json_responses) * self.PATCH_BUFFER_MULTIPLIER

        logger.debug(f"Calculated max_patches: {max_patches}")
        return max_patches

    def _find_initial_game_state_index(self, json_responses: list) -> Optional[int]:
        """
        Find the index of the first game state after game activation.

        The initial state is the response immediately following the UltActivateGameAction.

        Args:
            json_responses: List of (timestamp, response) tuples

        Returns:
            Index of initial game state, or None if not found
        """
        logger.info(f"Searching for {self.GAME_ACTIVATION_ACTION}...")
        initial_idx = -1

        for i, (_, json_response) in enumerate(json_responses):
            if json_response.get("action") == self.GAME_ACTIVATION_ACTION:
                initial_idx = i + 1
                logger.info(f"Found {self.GAME_ACTIVATION_ACTION} at index {i}, "
                            f"initial state at index {initial_idx}")

        if initial_idx != -1: return initial_idx

        logger.error(f"{self.GAME_ACTIVATION_ACTION} not found in recording")
        return None


    def _initialize_replay(
            self,
            output_file: Path,
            game_id: int,
            player_id: int,
            max_patches: int,
            static_map_data: StaticMapData
    ) -> Optional[Replay]:
        """Initialize replay database and record static map data."""
        logger.info("Initializing replay database...")

        try:
            replay = Replay(
                file_path=output_file,
                mode='w',
                game_id=game_id,
                player_id=player_id,
                max_patches=max_patches
            )
            replay.open()

            logger.info("Recording static map data to replay database")
            replay.record_static_map_data(
                static_map_data=static_map_data,
                game_id=game_id,
                player_id=player_id
            )

            return replay
        except Exception as e:
            logger.error(f"Failed to initialize replay: {e}")
            return None

    def _record_initial_state(
            self,
            replay: Replay,
            json_responses: list,
            initial_idx: int,
            game_id: int,
            player_id: int
    ) -> Optional[GameState]:
        """Parse and record the initial game state."""
        _, json_response = json_responses[initial_idx]

        # Create mock game interface for parsing context
        mock_game = GameInterface()

        try:
            # Parse initial game state
            initial_state: GameState = parse_any(
                GameState, json_response["result"], mock_game
            )
            current_timestamp = unix_ms_to_datetime(int(initial_state.time_stamp))

            logger.info(f"Recording initial game state at {current_timestamp} (game time)")

            # Record to replay database
            replay.record_initial_game_state(
                time_stamp=current_timestamp,
                game_id=game_id,
                player_id=player_id,
                game_state=initial_state
            )

            # Clear game references and update replay's last state
            GameObject.set_game_recursive(initial_state, None)
            replay.set_last_game_state(initial_state)
            replay.close()

            return initial_state
        except Exception as e:
            logger.error(f"Failed to record initial state: {e}")
            replay.close()
            return None

    def _reopen_replay_for_append(
            self,
            output_file: Path,
            game_id: int,
            player_id: int
    ) -> Optional[Replay]:
        """Reopen replay database in append mode."""
        logger.info("Reopening replay database in append mode...")

        try:
            replay = Replay(
                file_path=output_file,
                mode='a',
                game_id=game_id,
                player_id=player_id
            )
            replay.open()
            return replay
        except Exception as e:
            logger.error(f"Failed to reopen replay: {e}")
            return None

    def _process_json_responses(
            self,
            replay: Replay,
            json_responses: list,
            initial_idx: int,
            current_state: GameState,
            game_id: int,
            player_id: int
    ) -> bool:
        """
        Process JSON responses and create replay patches.

        Iterates through responses after the initial state, creating bidirectional
        patches that capture state changes. Handles both full state replacements
        and incremental updates.
        """
        # Create mock game interface for parsing
        mock_game = GameInterface()
        num_responses = len(json_responses) - initial_idx - 1

        logger.info(f"Processing {num_responses} state updates...")

        try:
            for i in tqdm(
                    range(initial_idx + 1, len(json_responses)),
                    desc="Writing Replay",
                    unit="patch",
                    unit_scale=True
            ):
                _, json_response = json_responses[i]

                # Verify no duplicate game activation
                if json_response.get("action") == self.GAME_ACTIVATION_ACTION:
                    logger.error(f"Found another {self.GAME_ACTIVATION_ACTION} at index {i}")
                    return False

                # Parse new state
                new_state: GameState = parse_any(
                    GameState, json_response["result"], mock_game
                )

                current_timestamp = unix_ms_to_datetime(int(new_state.time_stamp))

                # Create appropriate patch based on response type
                bipatch = self._create_patch(
                    json_response, current_state, new_state, i, current_timestamp
                )

                # Update current state if full replacement
                if json_response["result"]["@c"] == self.FULL_STATE_TYPE:
                    current_state = new_state

                # Record patch to replay database
                replay.append_patches(
                    time_stamp=current_timestamp,
                    game_id=game_id,
                    player_id=player_id,
                    replay_patches=[bipatch],
                )

            return True
        except Exception as e:
            logger.error(f"Failed to process JSON responses: {e}")
            return False

    def _create_patch(
            self,
            json_response: dict,
            current_state: GameState,
            new_state: GameState,
            response_idx: int,
            timestamp
    ) -> BidirectionalReplayPatch:
        """
        Create a bidirectional patch based on response type.

        Full state replacements use make_bireplay_patch for complete comparison.
        Incremental updates use GameState.update() to track specific changes.
        """
        if json_response["result"]["@c"] == self.FULL_STATE_TYPE:
            # Full state replacement - compare entire states
            logger.debug(f"Creating full state patch for response {response_idx} "
                         f"at {timestamp} (game time)")
            return make_bireplay_patch(current_state, new_state)
        else:
            # Incremental update - track specific changes
            logger.debug(f"Creating incremental patch for response {response_idx} "
                         f"at {timestamp} (game time)")
            bipatch = BidirectionalReplayPatch()
            current_state.update(new_state, path=[], rp=bipatch)
            return bipatch

    def _finalize_replay(self, replay: Replay, final_state: GameState) -> None:
        """Finalize replay database by recording final state and closing."""
        logger.info("Finalizing replay database...")
        GameObject.set_game_recursive(final_state, None)
        replay.set_last_game_state(final_state)
        replay.close()
        logger.info("Replay database finalized and closed")