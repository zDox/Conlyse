"""
Converter for transforming recorder data to replay format.
"""
from multiprocessing import Pool
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

from tqdm import tqdm

from conflict_interface.logger_config import get_logger
from enums import OperatingMode
from from_game_state_using_make_bipatch_to_replay import FromGameStateUsingMakeBiPatchToReplay
from from_json_responses_using_update_to_replay import FromJsonResponsesUsingUpdateToReplay
from from_recording_to_json import FromRecordingToJson
from recording_reader import RecordingReader

logger = get_logger()


class RecordingConverter:
    """
    Converts recorder data to specified output format.
    
    The recorder stores compressed game states and JSON responses in binary files.
    This converter reads those files and outputs them either as json or creates a Replay
    
    Supports three operating modes:
    - from_game_state_using_make_bipatch_to_replay:
        Converts the recording to a Replay using make_bireplay_patch between two consecutive game_states
    - from_json_responses_using_update_to_replay:
        Converts the recording to a Replay using the update function on a GameState
    - from_recording_to_json:
        Converts the recording to multiple json files
    """
    
    def __init__(
        self,
        recording_dir: str | Path,
        operating_mode: OperatingMode,
        use_tqdm: bool = True,
    ):
        """
        Initialize converter with recording directory.
        
        Args:
            recording_dir: Path to the recording directory
            operating_mode: One of the three operating modes
        """
        self.path = Path(recording_dir)
        # Controls whether tqdm-based progress bars are enabled for this converter.
        # In multiprocessing worker processes we usually disable tqdm to avoid garbled output.
        self._use_tqdm = use_tqdm
        self.reader = RecordingReader(self.path, use_tqdm=self._use_tqdm)
        self.op_mode = operating_mode

        self.check_op_mode_requirements()

    def check_op_mode_requirements(self):
        if not self.reader.recording_dir.exists():
            raise FileNotFoundError(f"Recording directory not found: {self.reader.recording_dir}")


        if self.op_mode == OperatingMode.gmr:
            if not self.reader.game_states_file.exists():
                raise FileNotFoundError(f"Game state file not found: {self.reader.game_states_file}, necessary in op mode gmr")
        # Op Mode rtj has no requirements as it simply tries to convert as much as it can

    def convert(self, output: Path, overwrite: bool, limit: int = None, game_id: int = None, player_id: int = None) -> bool:
        """
        Convert the recording to a replay file.
        
        Args:
            output: Path to the output replay database file or folder to dump the json to
            overwrite: Whether to overwrite existing output files
            limit: Maximum number of entries to process
            game_id: Game ID
            player_id: Player ID
            
        Returns:
            bool: True if successful, False otherwise
        """
        if self.op_mode in (OperatingMode.gmr, OperatingMode.rur) and Path(output).exists() and not overwrite:
            logger.error(f"Output file already exists: {output}")
            return False
        if self.op_mode == OperatingMode.gmr:
            gmr = FromGameStateUsingMakeBiPatchToReplay(self.reader, use_tqdm=self._use_tqdm)
            return gmr.convert(output_file=output,
                               overwrite=overwrite,
                               limit=limit,
                               game_id=game_id,
                               player_id=player_id)
        elif self.op_mode == OperatingMode.rur:
            rur = FromJsonResponsesUsingUpdateToReplay(self.reader, use_tqdm=self._use_tqdm)
            return rur.convert(output_file=output,
                               overwrite=overwrite,
                               limit=limit,
                               game_id=game_id,
                               player_id=player_id)
        elif self.op_mode == OperatingMode.rtj:
            rtj = FromRecordingToJson(self.reader, use_tqdm=self._use_tqdm)
            return rtj.convert(output_dir=output,
                               overwrite=overwrite,
                               limit=limit)
        else:
            logger.error(f"Invalid patch mode: {self.op_mode}")
            return False


def _convert_single_recording_worker(
    args: Tuple[Path, Path, OperatingMode, bool, Optional[int], Optional[int], Optional[int]],
) -> Tuple[Path, bool]:
    """
    Worker function to convert a single recording directory in a separate process.
    """
    (
        recording_dir,
        output_file,
        op_mode,
        overwrite,
        limit,
        game_id,
        player_id,
    ) = args

    try:
        # Disable tqdm inside worker processes to avoid clashing with the
        # main-process progress bar in bulk mode.
        converter = RecordingConverter(recording_dir, op_mode, use_tqdm=False)
        success = converter.convert(
            output=output_file,
            overwrite=overwrite,
            limit=limit,
            game_id=game_id,
            player_id=player_id,
        )
        return recording_dir, success
    except Exception as exc:  # pragma: no cover - defensive logging in worker
        logger.error("Failed to convert recording %s: %s", recording_dir, exc)
        return recording_dir, False


def convert_recordings_root(
    root: Path,
    output_dir: Path,
    op_mode: OperatingMode,
    processes: int,
    overwrite: bool = False,
    limit: Optional[int] = None,
    game_id: Optional[int] = None,
    player_id: Optional[int] = None,
    use_tqdm: bool = True,
    recording_name_filters: Optional[Sequence[str]] = None,
) -> bool:
    """
    Convert all recording subdirectories under a root directory into replay files.

    Each immediate child directory of ``root`` is treated as a recording directory.
    For each such directory ``<root>/<name>``, a replay file ``<output_dir>/<name>.db``
    is created using the requested operating mode.
    """
    root = Path(root)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if not root.exists():
        logger.error("Recordings root directory does not exist: %s", root)
        return False

    # Discover candidate recording directories.
    recording_dirs: List[Path] = [entry for entry in root.iterdir() if entry.is_dir()]

    # Optional filtering by recording directory names (e.g. specific games).
    if recording_name_filters:
        allowed_names = set(recording_name_filters)
        recording_dirs = [d for d in recording_dirs if d.name in allowed_names]

    if not recording_dirs:
        logger.warning("No recording subdirectories found under %s", root)
        return False

    jobs: List[Tuple[Path, Path, OperatingMode, bool, Optional[int], Optional[int], Optional[int]]] = []

    for recording_dir in recording_dirs:
        # Simple pre-filtering based on expected files for each mode.
        if op_mode == OperatingMode.gmr:
            if not (recording_dir / "game_states.bin").exists():
                logger.info(
                    "Skipping %s: game_states.bin not found (required for gmr mode)",
                    recording_dir,
                )
                continue
        elif op_mode == OperatingMode.rur:
            has_response_file = any(
                child.is_file() and child.name.startswith("responses")
                for child in recording_dir.iterdir()
            )
            if not has_response_file:
                logger.info(
                    "Skipping %s: no responses*.jsonl.zst files found (required for rur mode)",
                    recording_dir,
                )
                continue

        output_file = output_dir / f"{recording_dir.name}.bin"
        jobs.append(
            (
                recording_dir,
                output_file,
                op_mode,
                overwrite,
                limit,
                game_id,
                player_id,
            )
        )

    if not jobs:
        logger.warning(
            "No suitable recording directories found under %s for mode %s",
            root,
            op_mode,
        )
        return False

    # Normalize process count.
    if processes is None or processes < 1:
        processes = 1

    overall_success = True

    if processes == 1 or len(jobs) == 1:
        iterator = (_convert_single_recording_worker(job) for job in jobs)
        if use_tqdm:
            iterator = tqdm(
                iterator,
                total=len(jobs),
                desc="Recordings",
                unit="rec",
            )
        for recording_dir, success in iterator:
            if not success:
                overall_success = False
                logger.error("Conversion failed for recording %s", recording_dir)
    else:
        logger.info("Converting recordings using %d worker processes", processes)
        with Pool(processes=processes) as pool:
            iterator = pool.imap_unordered(_convert_single_recording_worker, jobs)
            if use_tqdm:
                iterator = tqdm(
                    iterator,
                    total=len(jobs),
                    desc="Recordings",
                    unit="rec",
                )
            for recording_dir, success in iterator:
                if not success:
                    overall_success = False
                    logger.error("Conversion failed for recording %s", recording_dir)

    if overall_success:
        logger.info(
            "Finished converting %d recording(s) under %s into %s",
            len(jobs),
            root,
            output_dir,
        )
    else:
        logger.error(
            "Completed conversion of recordings under %s with failures; see log for details",
            root,
        )

    return overall_success

