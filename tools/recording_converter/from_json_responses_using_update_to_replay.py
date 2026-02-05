from pathlib import Path
from typing import Optional

from tqdm import tqdm

from conflict_interface.data_types.static_map_data import StaticMapData
from conflict_interface.replay.replay_builder import ReplayBuilder
from tools.recording_converter.recorder_logger import get_logger
from tools.recording_converter.recording_reader import RecordingReader

logger = get_logger()


class FromJsonResponsesUsingUpdateToReplay:
    """
    Converts game recordings from JSON responses to replay format using ReplayBuilder.

    This converter processes JSON responses containing game state updates and creates
    bidirectional replay patches using the ReplayBuilder class.
    """

    # Constants
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
        Convert recording to replay using ReplayBuilder.

        This method uses ReplayBuilder to handle all replay creation and patching logic.

        Args:
            output_file: Path to the output replay file
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

        # Calculate max_patches for replay
        max_patches = self._calculate_max_patches(json_responses, limit)

        # Create ReplayBuilder
        builder = ReplayBuilder(
            path=output_file,
            game_id=game_id,
            player_id=player_id
        )

        try:
            # Create initial replay with static map data
            logger.info("Creating initial replay...")
            builder.create_replay(
                json_responses=json_responses,
                static_map_data=static_map_data,
                max_patches=max_patches
            )

            # Append remaining JSON responses
            logger.info("Appending JSON responses...")

            def progress_callback(current: int, total: int):
                """Progress callback for tqdm integration"""
                pass  # tqdm will be handled in append_json_responses

            # Use tqdm for progress reporting
            with tqdm(total=len(json_responses), desc="Writing Replay", unit="patch", unit_scale=True) as pbar:
                def wrapped_callback(current: int, total: int):
                    pbar.n = current
                    pbar.refresh()

                builder.append_json_responses(
                    json_responses=json_responses,
                    progress_callback=wrapped_callback
                )
                pbar.n = len(json_responses)
                pbar.refresh()

            logger.info(f"Successfully converted recording to replay: {output_file}")
            return True

        except Exception as e:
            logger.error(f"Failed to convert recording: {e}")
            return False

    def _calculate_max_patches(self, json_responses: list, limit: Optional[int]) -> int:
        """Calculate maximum number of patches needed for replay."""
        if limit:
            max_patches = limit * self.PATCH_BUFFER_MULTIPLIER
        else:
            max_patches = len(json_responses) * self.PATCH_BUFFER_MULTIPLIER

        logger.debug(f"Calculated max_patches: {max_patches}")
        return max_patches

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

