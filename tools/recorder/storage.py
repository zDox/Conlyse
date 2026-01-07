"""
Storage management for recording sessions.
"""
import json
import logging
import pickle
import sys
import threading
from datetime import UTC
from datetime import datetime
from pathlib import Path

import zstandard as zstd
from orjson import orjson

from conflict_interface.data_types.game_state.game_state import GameState
from conflict_interface.data_types.static_map_data import StaticMapData
from tools.recorder.recorder_logger import get_logger

logger = get_logger()


class RecordingStorage:
    """
    Handles storage of recorded game data.

    Files generated:
    - game_states.bin: Compressed pickle dumps of GameState objects with timestamps
    - requests.jsonl.zst: Compressed JSON lines of request parameters sent to server
    - responses.jsonl.zst: Compressed JSON lines of responses from server
    - static_map_data.bin: Compressed pickle dump of StaticMapData
    - metadata.json: Recording metadata including timestamps
    - recording.log: Recorder tool log
    - library.log: ConflictInterface library log
    """

    def __init__(self, output_path: str, save_game_states: bool = False):
        """
        Initialize recording storage.
        
        Args:
            output_path: Path to the output directory for recordings
        """
        self.output_path = Path(output_path)
        self.output_path.mkdir(parents=True, exist_ok=True)
        
        # Create compressor
        self._compressor = zstd.ZstdCompressor(level=3)
        
        # Storage for game states and responses
        self.game_states_file = self.output_path / "game_states.bin"
        self.requests_file = self.output_path / "requests.jsonl.zst"
        self.responses_file = self.output_path / "responses.jsonl.zst"
        self.static_map_data_file = self.output_path / "static_map_data.bin"
        self.metadata_file = self.output_path / "metadata.json"

        self.recorder_log_file = self.output_path / "recording.log"
        self.library_log_file = self.output_path / "library.log"
        self.recorder_log_file_handler = None
        self.library_log_file_handler = None
        self.log_thread_id: int | None = None
        self.resume_metadata: dict = {}

        self.save_game_states = save_game_states

        # MEMORY OPTIMIZATION: Cache metadata in memory and batch writes
        self._metadata_cache = None
        self._metadata_lock = threading.Lock()
        self._pending_updates = []
        self._metadata_batch_size = 100  # Write metadata every N updates

        # Initialize files
        self._init_files()

    def _init_files(self):
        """Initialize recording files."""
        # Create metadata
        metadata = {
            "version": "1.0",
            "created_at": datetime.now().isoformat(),
            "updates": []
        }
        self._metadata_cache = metadata
        self._save_metadata(metadata)

    def _save_metadata(self, metadata: dict):
        """Save metadata to file."""
        with open(self.metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)

    def _load_metadata(self) -> dict:
        """Load metadata from file or cache."""
        if self._metadata_cache is not None:
            return self._metadata_cache

        if self.metadata_file.exists():
            with open(self.metadata_file, 'r') as f:
                self._metadata_cache = json.load(f)
                return self._metadata_cache
        return {"version": "1.0", "updates": []}

    def update_resume_metadata(self, resume: dict):
        """
        Persist resume information (auth, cookies, replay path, etc.) to metadata.json.
        """
        with self._metadata_lock:
            metadata = self._load_metadata()
            metadata["resume"] = resume
            self._metadata_cache = metadata
            self._save_metadata(metadata)
            self.resume_metadata = resume

    def reset_compressor(self):
        self._compressor = zstd.ZstdCompressor(level=3)

    @staticmethod
    def append_bytes_to_file(file_path: Path, timestamp_ms: int, data: bytes):
        with open(file_path, 'ab') as f:
            # Write timestamp and length, then compressed data
            f.write(timestamp_ms.to_bytes(8, 'big'))
            f.write(len(data).to_bytes(4, 'big'))
            f.write(data)

    def save_game_state(self, timestamp: float, game_state: GameState):
        if not self.save_game_states:
            return

        # MEMORY OPTIMIZATION: Minimize time holding references
        ritf = game_state.game
        game_state.set_game(None)
        try:
            game_state_bytes = pickle.dumps(game_state)
            compressed_state = self._compressor.compress(game_state_bytes)
            # Clear the bytes immediately after compression
            del game_state_bytes
        finally:
            game_state.set_game(ritf)

        timestamp_ms = int(timestamp * 1000)
        self.append_bytes_to_file(self.game_states_file, timestamp_ms, compressed_state)

        # Clear compressed data
        del compressed_state

        logger.info(f"Saved game state at timestamp {timestamp}")

    def save_request_response(self, timestamp: float, request_json: dict, response_json: dict):
        # MEMORY OPTIMIZATION: Process and write immediately without holding references
        timestamp_ms = int(timestamp * 1000)

        # Process request
        request_str = json.dumps(request_json)
        compressed_request = self._compressor.compress(request_str.encode("utf-8"))
        self.append_bytes_to_file(self.requests_file, timestamp_ms, compressed_request)
        del request_str, compressed_request, request_json

        # Process response
        response_str = json.dumps(response_json)
        compressed_response = self._compressor.compress(response_str.encode("utf-8"))
        self.append_bytes_to_file(self.responses_file, timestamp_ms, compressed_response)
        del response_str, compressed_response, response_json

        # MEMORY OPTIMIZATION: Batch metadata updates
        with self._metadata_lock:
            self._pending_updates.append({
                "timestamp": timestamp,
                "datetime": datetime.fromtimestamp(timestamp, tz=UTC).isoformat()
            })

            # Only write metadata periodically to reduce I/O and memory churn
            if len(self._pending_updates) >= self._metadata_batch_size:
                self._flush_metadata_updates()

    def _flush_metadata_updates(self):
        """Flush pending metadata updates to disk."""
        if not self._pending_updates:
            return

        metadata = self._load_metadata()
        metadata["updates"].extend(self._pending_updates)
        self._pending_updates.clear()
        self._metadata_cache = metadata
        self._save_metadata(metadata)

    def setup_logging(self):
        library_logger = logging.getLogger("con_itf")
        recording_logger = logging.getLogger("rec")

        self.log_thread_id = threading.get_ident()
        allowed_thread = self.log_thread_id

        def add_file_handler(logger, filename, level=logging.DEBUG, formatter=None):
            file_handler = logging.FileHandler(filename)
            file_handler.setLevel(level)
            if formatter is None:
                formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
            file_handler.setFormatter(formatter)
            file_handler.addFilter(
                lambda record, allowed_thread=allowed_thread: allowed_thread is None
                or getattr(record, "thread", threading.get_ident()) == allowed_thread
            )
            logger.addHandler(file_handler)
            return file_handler

        # Add file handlers when ready
        self.library_log_file_handler = add_file_handler(library_logger, self.library_log_file)
        self.recorder_log_file_handler = add_file_handler(recording_logger, self.recorder_log_file)

        logger.info(f"Log recording started to: {self.recorder_log_file}")
        library_logger.info(f"Library log recording started to: {self.library_log_file}")

    def save_static_map_data(self, static_map_data: StaticMapData):
        """
        Save static map data to file.

        Args:
            static_map_data: The static map data object
        """
        # MEMORY OPTIMIZATION: Minimize time holding references
        ritf = static_map_data.game
        static_map_data.set_game(None)
        try:
            static_map_data_bytes = pickle.dumps(static_map_data)
            compressed_data = self._compressor.compress(static_map_data_bytes)
            # Clear bytes immediately
            del static_map_data_bytes
        finally:
            static_map_data.set_game(ritf)

        # Write to file
        with open(self.static_map_data_file, 'wb') as f:
            f.write(compressed_data)

        # Clear compressed data
        del compressed_data

        logger.info("Saved static map data")

    def teardown_logging(self):
        """Remove the file logging handler and flush remaining metadata."""
        # MEMORY OPTIMIZATION: Flush any remaining metadata updates
        with self._metadata_lock:
            self._flush_metadata_updates()

        if self.recorder_log_file_handler:
            logger.info("Log recording completed")
            logger.removeHandler(self.recorder_log_file_handler)
            self.recorder_log_file_handler.close()
            self.recorder_log_file_handler = None

        if self.library_log_file_handler:
            library_logger = logging.getLogger("con_itf")
            library_logger.info("Library log recording completed")
            library_logger.removeHandler(self.library_log_file_handler)
            self.library_log_file_handler.close()
            self.library_log_file_handler = None

        # Clear caches
        self._metadata_cache = None
        self._pending_updates = None