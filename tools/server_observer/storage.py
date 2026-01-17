"""
Storage management for recording sessions.
"""
import json
import logging
import pickle
import shutil
import threading
import time
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import Optional

import zstandard as zstd

from conflict_interface.data_types.static_map_data import StaticMapData
from tools.server_observer.recorder_logger import get_logger

logger = get_logger()


class RecordingStorage:
    """
    Handles storage of recorded game data.

    Files generated:
    - requests.jsonl.zst: Compressed JSON lines of request parameters sent to server
    - responses.jsonl.zst: Compressed JSON lines of responses from server
    - static_map_data.bin: Compressed pickle dump of StaticMapData
    - metadata.json: Recording metadata including timestamps
    - recording.log: Recorder tool log
    - library.log: ConflictInterface library log
    """

    def __init__(self, output_path: Path, overwrite: bool = False, metadata_path: Optional[Path] = None,
                 long_term_storage_path: Optional[Path] = None, file_size_threshold: Optional[int] = None):
        """
        Initialize recording storage.
        
        Args:
            output_path: Path to the output directory for response files 
                         (responses.jsonl.zst, requests.jsonl.zst, game_states.bin, static_map_data.bin)
            overwrite: Whether to overwrite existing files
            metadata_path: Optional separate path for metadata files 
                          (metadata.json, recording.log, library.log). 
                          If None, uses output_path for all files.
            long_term_storage_path: Optional path for long-term storage of large response files.
                                   If set, files exceeding file_size_threshold will be moved here.
            file_size_threshold: Size threshold in bytes. When responses file exceeds this size,
                                it will be moved to long_term_storage_path and a new file created.
        """
        self.output_path = output_path
        self.output_path.mkdir(parents=True, exist_ok=True)
        
        # Metadata path can be separate from responses path
        self.metadata_path = metadata_path if metadata_path is not None else output_path
        self.metadata_path.mkdir(parents=True, exist_ok=True)
        
        # Long-term storage configuration validation
        if (long_term_storage_path is None) != (file_size_threshold is None):
            raise ValueError(
                "Both 'long_term_storage_path' and 'file_size_threshold' must be provided together, "
                "or neither should be provided. Cannot use one without the other."
            )
        
        if file_size_threshold is not None and file_size_threshold <= 0:
            raise ValueError(f"file_size_threshold must be positive, got {file_size_threshold}")
        
        self.long_term_storage_path = long_term_storage_path
        self.file_size_threshold = file_size_threshold
        self._file_sequence = 0  # Track sequence number for rotated files
        
        # Create compressor
        self._compressor = zstd.ZstdCompressor(level=3)
        
        # Storage for game states and responses (in output_path)
        self.game_states_file = self.output_path / "game_states.bin"
        self.requests_file = self.output_path / "requests.jsonl.zst"
        self.responses_file = self.output_path / "responses.jsonl.zst"
        self.static_map_data_file = self.output_path / "static_map_data.bin"
        
        # Metadata files (in metadata_path)
        self.metadata_file = self.metadata_path / "metadata.json"
        self.recorder_log_file = self.metadata_path / "recording.log"
        self.library_log_file = self.metadata_path / "library.log"
        
        self.recorder_log_file_handler = None
        self.library_log_file_handler = None
        self.log_thread_id: int | None = None
        self.resume_metadata: dict = {}
        self._metadata_cache: dict = None  # Cache metadata to avoid repeated file reads

        # Initialize files
        if overwrite or not self.metadata_file.exists():
            self._init_files()
        self._load_metadata()
        self._restore_file_sequence()

    def _init_files(self):
        """Initialize recording files."""
        # Create metadata
        metadata = {
            "version": "1.0",
            "created_at": datetime.now().isoformat(),
            "updates": [],
        }
        self._save_metadata(metadata)

    def _save_metadata(self, metadata: dict):
        """Save metadata to file."""
        with open(self.metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        # Update cache when saving
        self._metadata_cache = metadata

    def _load_metadata(self) -> dict:
        """Load metadata from file or cache."""
        # Return cached metadata if available to avoid repeated file I/O
        if self._metadata_cache is not None:
            return self._metadata_cache
            
        if self.metadata_file.exists():
            with open(self.metadata_file, 'r') as f:
                self._metadata_cache = json.load(f)
                self.resume_metadata = self._metadata_cache.get("resume", {})
                return self._metadata_cache
        else:
            logger.warning(f"Metadata file not found: {self.metadata_file}")
        
        self._metadata_cache = {"version": "1.0", "updates": []}
        return self._metadata_cache

    def update_resume_metadata(self, resume: dict):
        """
        Persist resume information (auth, cookies, replay path, etc.) to metadata.json.
        """
        metadata = self._load_metadata()
        metadata["resume"] = resume
        self._save_metadata(metadata)
        self.resume_metadata = resume

    def get_resume_metadata(self) -> dict:
        return self.resume_metadata

    def has_resume_metadata(self) -> bool:
        return "resume" in self._load_metadata() and self.resume_metadata != {}

    def _restore_file_sequence(self):
        """Restore the file sequence number from metadata."""
        metadata = self._load_metadata()
        self._file_sequence = metadata.get("file_sequence", 0)

    def _update_file_sequence(self):
        """Increment and persist the file sequence number."""
        self._file_sequence += 1
        metadata = self._load_metadata()
        metadata["file_sequence"] = self._file_sequence
        self._save_metadata(metadata)

    def _get_file_size(self, file_path: Path) -> int:
        """Get the size of a file in bytes."""
        try:
            return file_path.stat().st_size if file_path.exists() else 0
        except Exception as e:
            logger.warning(f"Failed to get file size for {file_path}: {e}")
            return 0

    def _should_rotate_file(self) -> bool:
        """Check if the responses file should be rotated to long-term storage."""
        if self.long_term_storage_path is None or self.file_size_threshold is None:
            return False
        
        current_size = self._get_file_size(self.responses_file)
        return current_size >= self.file_size_threshold

    def _rotate_to_long_term_storage(self):
        """Move current responses file to long-term storage and create a new one."""
        if not self.responses_file.exists():
            return
        
        # Get file size before moving
        file_size = self._get_file_size(self.responses_file)
        
        # Create long-term storage directory with same structure as output_path
        # The relative path from parent to output_path is preserved
        game_dir_name = self.output_path.name
        lts_game_dir = self.long_term_storage_path / game_dir_name
        lts_game_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate filename with sequence number
        self._update_file_sequence()
        lts_filename = f"responses_{self._file_sequence:04d}.jsonl.zst"
        lts_file_path = lts_game_dir / lts_filename
        
        # Move the file to long-term storage
        try:
            shutil.move(str(self.responses_file), str(lts_file_path))
            logger.info(f"Rotated responses file to long-term storage: {lts_file_path}")
            
            # Log the rotation in metadata
            metadata = self._load_metadata()
            if "rotations" not in metadata:
                metadata["rotations"] = []
            metadata["rotations"].append({
                "sequence": self._file_sequence,
                "timestamp": time.time(),
                "datetime": datetime.now(UTC).isoformat(),
                "destination": str(lts_file_path),
                "size_bytes": file_size
            })
            self._save_metadata(metadata)
        except Exception as e:
            logger.error(f"Failed to rotate file to long-term storage: {e}")
            raise

    @staticmethod
    def append_bytes_to_file(file_path: Path, timestamp: int, data: bytes):
        with open(file_path, 'ab') as f:
            # Write timestamp and length, then compressed data
            f.write(timestamp.to_bytes(8, 'big'))
            f.write(len(data).to_bytes(4, 'big'))
            f.write(data)

    def save_response(self, response: dict):
        """Save response to file."""
        # Check if file rotation is needed before saving
        if self._should_rotate_file():
            self._rotate_to_long_term_storage()
        
        response_str = json.dumps(response)
        response_compressed = self._compressor.compress(response_str.encode("utf-8"))
        self.append_bytes_to_file(self.responses_file, int(time.time()), response_compressed)

        metadata = self._load_metadata()
        metadata["updates"].append({
            "timestamp": time.time(),
            "datetime": datetime.now(UTC).isoformat()
        })
        self._save_metadata(metadata)

    def setup_logging(self):
        recording_logger = logging.getLogger("sro")

        self.log_thread_id = threading.get_ident()
        allowed_thread = self.log_thread_id

        def add_file_handler(logger, filename, level=logging.INFO, formatter=None):
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
        self.recorder_log_file_handler = add_file_handler(recording_logger, self.recorder_log_file)

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
        if self.recorder_log_file_handler:
            logger.removeHandler(self.recorder_log_file_handler)
            self.recorder_log_file_handler.close()
            self.recorder_log_file_handler = None

        if self.library_log_file_handler:
            library_logger = logging.getLogger("con_itf")
            library_logger.removeHandler(self.library_log_file_handler)
            self.library_log_file_handler.close()
            self.library_log_file_handler = None