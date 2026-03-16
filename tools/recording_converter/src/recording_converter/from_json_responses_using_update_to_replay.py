from __future__ import annotations

from pathlib import Path


from typing import Optional
from typing import TYPE_CHECKING

from tqdm import tqdm

from conflict_interface.replay.replay_builder import ReplayBuilder
from conflict_interface.replay.response_metadata import ResponseMetadata
from .recorder_logger import get_logger
from .recording_reader import RecordingReader

if TYPE_CHECKING:
    from conflict_interface.data_types.newest.static_map_data import StaticMapData

logger = get_logger()


class FromJsonResponsesUsingUpdateToReplay:
    """
    Converts game recordings from JSON responses to replay format using ReplayBuilder.

    This converter processes JSON responses containing game state updates and creates
    bidirectional replay patches using the ReplayBuilder class.
    """

    # Constants
    PATCH_BUFFER_MULTIPLIER = 2

    def __init__(self, recording_reader: RecordingReader, use_tqdm: bool = True):
        """
        Initialize the converter with a recording reader.

        Args:
            recording_reader: Reader instance for accessing recording data
        """
        self.reader = recording_reader
        self._use_tqdm = use_tqdm

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
            game_id: Optional explicit game ID override
            player_id: Optional explicit player ID override

        Returns:
            True if conversion succeeded, False otherwise
        """
        # Load JSON responses from recording
        json_responses = self._load_json_responses(limit)
        if json_responses is None:
            return False

        # Derive game_id and player_id from ResponseMetadata if not provided.
        if game_id is None or player_id is None:
            inferred_game_id, inferred_player_id = self._infer_ids_from_metadata(json_responses)
            if inferred_game_id is None or inferred_player_id is None:
                logger.error("Unable to determine game_id/player_id from ResponseMetadata")
                return False

            if game_id is None:
                game_id = inferred_game_id
            if player_id is None:
                player_id = inferred_player_id

        logger.info(f"Converting recording: game_id={game_id}, player_id={player_id}")

        # Prepare output file
        if not self._prepare_output_file(output_file, overwrite):
            return False

        # Create ReplayBuilder
        builder = ReplayBuilder(
            path=output_file,
            game_id=game_id,
            player_id=player_id,
        )

        # Create initial replay with static map data
        logger.info("Creating initial replay...")
        initial_index = builder.create_replay(
            json_responses=json_responses,
        )

        # Append remaining JSON responses (skip the initial state already processed)
        logger.info("Appending JSON responses...")
        remaining_responses = json_responses[initial_index + 1:] if initial_index + 1 < len(json_responses) else []

        # Use tqdm for progress reporting (optional)
        if self._use_tqdm:
            with tqdm(
                total=len(remaining_responses),
                desc="Writing Replay",
                unit="patch",
                unit_scale=True,
            ) as pbar:
                def wrapped_callback(current: int, total: int):
                    pbar.n = current
                    pbar.refresh()

                builder.append_json_responses(
                    json_responses=remaining_responses,
                    progress_callback=wrapped_callback,
                )
                pbar.n = len(remaining_responses)
                pbar.refresh()
        else:
            builder.append_json_responses(
                json_responses=remaining_responses,
                progress_callback=None,
            )

        logger.info(f"Successfully converted recording to replay: {output_file}")
        return True

    def _calculate_max_patches(self, json_responses: list, limit: Optional[int]) -> int:
        """Calculate maximum number of patches needed for replay."""
        if limit:
            max_patches = limit * self.PATCH_BUFFER_MULTIPLIER
        else:
            max_patches = len(json_responses) * self.PATCH_BUFFER_MULTIPLIER

        logger.debug(f"Calculated max_patches: {max_patches}")
        return max_patches

    @staticmethod
    def _infer_ids_from_metadata(json_responses: list[tuple[ResponseMetadata, dict]]) -> tuple[Optional[int], Optional[int]]:
        """
        Infer game_id and player_id from the ResponseMetadata stream.

        Uses the first response as the source of truth and logs a warning
        if subsequent entries disagree.
        """
        if not json_responses:
            return None, None

        first_meta, _ = json_responses[0]
        game_id = int(first_meta.game_id)
        player_id = int(first_meta.player_id)

        inconsistent = False
        for meta, _ in json_responses[1:]:
            if meta.game_id != game_id or meta.player_id != player_id:
                inconsistent = True
                break

        if inconsistent:
            logger.warning(
                "Inconsistent game_id/player_id detected in ResponseMetadata; "
                f"using first values game_id={game_id}, player_id={player_id}"
            )

        return game_id, player_id

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

