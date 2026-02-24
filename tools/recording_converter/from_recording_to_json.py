import json
from pathlib import Path
import shutil

from tqdm import tqdm

from conflict_interface.data_types.newest.to_json import dump_any # TODO dumping is only allowed inside datatypes
from conflict_interface.utils.helper import unix_ms_to_datetime
from tools.recording_converter.recorder_logger import get_logger
from tools.recording_converter.recording_reader import RecordingReader

logger = get_logger()

# Just a note: Converting is the process of reading data and then dumping it to JSON files.

class FromRecordingToJson:
    def __init__(self, recording_reader: RecordingReader):
        self.reader = recording_reader
        self.game_states_dir = None
        self.json_requests_dir = None
        self.json_responses_dir = None

    def setup_output_dir(self, output_dir, overwrite: bool):
        # Set up output directory
        if output_dir is None:
            output_dir = self.reader.recording_dir / "json_dumps"
        else:
            output_dir = Path(output_dir)
        if output_dir.exists() and overwrite:
            shutil.rmtree(output_dir)
        elif output_dir.exists() and not overwrite:
            raise FileExistsError(f"Output directory already exists: {output_dir}")

        output_dir.mkdir(parents=True)

        # Create subdirectories
        self.game_states_dir = output_dir / "game_states"
        self.json_requests_dir = output_dir / "json_requests"
        self.json_responses_dir = output_dir / "json_responses"
        self.game_states_dir.mkdir(exist_ok=True)
        self.json_requests_dir.mkdir(exist_ok=True)
        self.json_responses_dir.mkdir(exist_ok=True)

        logger.info(f"Output directory: {output_dir}")

    def dump_game_state_to_json(self, index: int, len_game_states: int):
        timestamp_ms, game_state = self.reader.read_game_state(index)
        timestamp_dt = unix_ms_to_datetime(timestamp_ms)

        # Create filename with timestamp
        filename = f"game_state_{index:04d}_{timestamp_ms}.json"
        output_file = self.game_states_dir / filename

        # Dump game state to JSON using dump_any
        json_data = dump_any(game_state)

        # Add metadata
        output_data = {
            "timestamp_ms": timestamp_ms,
            "timestamp_iso": timestamp_dt.isoformat(),
            "state_index": index,
            "game_state": json_data
        }

        # Write to file
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)

    def dump_requests_to_json(self, json_requests):
        for i in tqdm(range(len(json_requests)), desc="Dumping JSON requests: ", unit="Request", unit_scale=True):
            timestamp_ms, json_request = json_requests[i]
            timestamp_dt = unix_ms_to_datetime(timestamp_ms)

            # Create filename with timestamp
            filename = f"request_{i:04d}_{timestamp_ms}.json"
            output_file = self.json_requests_dir / filename

            # Add metadata
            output_data = {
                "timestamp_ms": timestamp_ms,
                "timestamp_iso": timestamp_dt.isoformat(),
                "request_index": i,
                "request": json_request
            }

            # Write to file
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)

    def dump_responses_to_json(self, json_responses):
        for i in tqdm(range(len(json_responses)), desc="Dumping JSON responses: ", unit="Response", unit_scale=True):
            timestamp_ms, json_response = json_responses[i]
            timestamp_dt = unix_ms_to_datetime(timestamp_ms)

            # Create filename with timestamp
            filename = f"response_{i:04d}_{timestamp_ms}.json"
            output_file = self.json_responses_dir / filename

            # Add metadata
            output_data = {
                "timestamp_ms": timestamp_ms,
                "timestamp_iso": timestamp_dt.isoformat(),
                "response_index": i,
                "response": json_response
            }

            # Write to file
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)

        logger.info(f"Successfully dumped {len(json_responses)} JSON responses to {self.json_responses_dir}")

    def convert(self, output_dir: Path = None, overwrite: bool = False, limit: int = None) -> bool:
        """
        Dump game states, JSON requests and JSON responses to separate JSON files.

        Args:
            output_dir: Directory to save JSON files (defaults to recording_dir/json_dumps)
            overwrite: Whether to overwrite existing files
            limit: Limit number of game states, JSON responses and JSON requests to process (defaults to all)
game
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.setup_output_dir(output_dir, overwrite)

            # Dump game states
            len_game_states = self.reader.len_game_states()
            game_states_to_process = len_game_states if limit is None else min(limit, len_game_states)
            if len_game_states != 0:
                for i in tqdm(range(game_states_to_process), desc="Dumping Game States: ", unit="State", unit_scale=True):
                    self.dump_game_state_to_json(i, game_states_to_process)
            else:
                logger.info(f"No Game states found in recording")

            # Dump JSON requests if available
            if self.reader.requests_file.exists():
                json_requests = self.reader.read_json_requests(limit)
                if json_requests:
                    self.dump_requests_to_json(json_requests)
                else:
                    logger.warning("No JSON requests found in recording")
            else:
                logger.info("No JSON requests file found in recording")

            # Dump JSON responses if available
            json_responses = self.reader.read_json_responses(limit)
            if json_responses:
                self.dump_responses_to_json(json_responses)
            else:
                logger.warning("No JSON responses found in recording")
            return True

        except Exception as e:
            logger.error(f"Error dumping to JSON: {e}", exc_info=True)
            return False
