import json
from pathlib import Path

from conflict_interface.data_types.game_object import dump_any
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
            output_dir.rmdir()
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

        logger.info(f"Converting state {index + 1}/{len_game_states} to {filename}")

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
        len_json_requests = len(json_requests)
        for i, (timestamp_ms, json_request) in enumerate(json_requests):
            timestamp_dt = unix_ms_to_datetime(timestamp_ms)

            # Create filename with timestamp
            filename = f"request_{i:04d}_{timestamp_ms}.json"
            output_file = self.json_requests_dir / filename

            logger.info(f"Dumping request {i + 1}/{len_json_requests} to {filename}")

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
        logger.info(f"Converting {len(json_responses)} JSON responses")

        for i, (timestamp_ms, json_response) in enumerate(json_responses):
            timestamp_dt = unix_ms_to_datetime(timestamp_ms)

            # Create filename with timestamp
            filename = f"response_{i:04d}_{timestamp_ms}.json"
            output_file = self.json_responses_dir / filename

            logger.info(f"Dumping response {i + 1}/{len(json_responses)} to {filename}")

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

    def convert(self, output_dir: str = None, overwrite: bool = False) -> bool:
        """
        Dump game states, JSON requests, and JSON responses to separate JSON files.

        Args:
            output_dir: Directory to save JSON files (defaults to recording_dir/json_dumps)
            overwrite: Whether to overwrite existing files

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.setup_output_dir(output_dir, overwrite)

            # Dump game states
            len_game_states = self.reader.len_game_states()
            if len_game_states != 0:
                for i in range(len_game_states):
                    self.dump_game_state_to_json(i, len_game_states)
                logger.info(f"Successfully dumped {len_game_states} game states to {self.game_states_dir}")
            else:
                logger.info(f"No Game states found in recording")

            # Dump JSON requests if available
            if self.reader.requests_file.exists():
                json_requests = self.reader.read_json_requests()
                if json_requests:
                    logger.info(f"Dumping {len(json_requests)} JSON requests")

                    self.dump_requests_to_json(json_requests)

                    logger.info(f"Successfully dumped {len(json_requests)} JSON requests to {self.json_requests_dir}")
                else:
                    logger.warning("No JSON requests found in recording")
            else:
                logger.info("No JSON requests file found in recording")

            # Dump JSON responses if available
            if self.reader.responses_file.exists():
                json_responses = self.reader.read_json_responses()
                if json_responses:
                    self.dump_responses_to_json(json_responses)
                else:
                    logger.warning("No JSON responses found in recording")
            else:
                logger.info("No JSON responses file found in recording")
            return True

        except Exception as e:
            logger.error(f"Error dumping to JSON: {e}", exc_info=True)
            return False
