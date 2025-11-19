"""
Storage management for recording sessions.
"""
import json
import logging
import pickle
from datetime import datetime
from pathlib import Path
from typing import Optional

import zstandard as zstd

from conflict_interface.data_types.game_state.game_state import GameState
from conflict_interface.logger_config import get_logger

logger = get_logger()


class RecordingStorage:
    """Handles storage of recorded game data."""
    
    def __init__(self, output_path: str):
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
        self.responses_file = self.output_path / "responses.jsonl.zst"
        self.metadata_file = self.output_path / "metadata.json"
        self.log_file = self.output_path / "recording.log"
        
        # Log handler for capturing logs
        self.log_handler: Optional[logging.FileHandler] = None
        
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
        self._save_metadata(metadata)
    
    def _save_metadata(self, metadata: dict):
        """Save metadata to file."""
        with open(self.metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
    
    def _load_metadata(self) -> dict:
        """Load metadata from file."""
        if self.metadata_file.exists():
            with open(self.metadata_file, 'r') as f:
                return json.load(f)
        return {"version": "1.0", "updates": []}
    
    def save_update(self, game_state: GameState, response_json: dict, timestamp: float):
        """
        Save a game update with compressed game state and response.
        
        Args:
            game_state: The game state object
            response_json: The JSON response from the server
            timestamp: Timestamp of the update
        """
        # Compress and save game state
        ritf = game_state.game
        game_state.set_game(None)
        game_state_bytes = pickle.dumps(game_state)
        game_state.set_game(ritf)
        compressed_state = self._compressor.compress(game_state_bytes)
        
        # Convert timestamp to integer milliseconds
        timestamp_ms = int(timestamp * 1000)
        
        with open(self.game_states_file, 'ab') as f:
            # Write timestamp and length, then compressed data
            f.write(timestamp_ms.to_bytes(8, 'big'))
            f.write(len(compressed_state).to_bytes(4, 'big'))
            f.write(compressed_state)
        
        # Compress and save JSON response
        response_str = json.dumps(response_json)
        compressed_response = self._compressor.compress(response_str.encode('utf-8'))
        
        with open(self.responses_file, 'ab') as f:
            # Write timestamp and length, then compressed data
            f.write(timestamp_ms.to_bytes(8, 'big'))
            f.write(len(compressed_response).to_bytes(4, 'big'))
            f.write(compressed_response)
        
        # Update metadata
        metadata = self._load_metadata()
        metadata["updates"].append({
            "timestamp": timestamp,
            "datetime": datetime.fromtimestamp(timestamp).isoformat()
        })
        self._save_metadata(metadata)
        
        logger.info(f"Saved update at timestamp {timestamp}")
    
    def setup_logging(self):
        """Set up file logging for the recording session."""
        # Create a file handler for the log file
        self.log_handler = logging.FileHandler(self.log_file, mode='w', encoding='utf-8')
        self.log_handler.setLevel(logging.DEBUG)
        
        # Use the same format as the console handler
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s.%(module)s - %(levelname)s - %(message)s"
        )
        self.log_handler.setFormatter(formatter)
        
        # Add the handler to the logger
        logger.addHandler(self.log_handler)
        logger.info(f"Log recording started to: {self.log_file}")
    
    def teardown_logging(self):
        """Remove the file logging handler."""
        if self.log_handler:
            logger.info("Log recording completed")
            logger.removeHandler(self.log_handler)
            self.log_handler.close()
            self.log_handler = None
