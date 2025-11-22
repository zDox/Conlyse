import json
import pickle
from pathlib import Path
from typing import List
from typing import Optional
from typing import Tuple

import zstandard as zstd

from conflict_interface.data_types.game_state.game_state import GameState
from conflict_interface.data_types.static_map_data import StaticMapData
from tools.recording_converter.recorder_logger import get_logger

logger = get_logger()

class RecordingReader:
    def __init__(self, recording_dir):
        self.recording_dir = Path(recording_dir)
        self.game_states_file = self.recording_dir / "game_states.bin"
        self.requests_file = self.recording_dir / "requests.jsonl.zst"
        self.responses_file = self.recording_dir / "responses.jsonl.zst"
        self.static_map_data_file = self.recording_dir / "static_map_data.bin"

        self._decompressor = zstd.ZstdDecompressor()

    def read_static_map_data(self) -> Optional[StaticMapData]:
        """
        Read static map data from the recording.

        Returns:
            StaticMapData object or None if not found
        """
        if not self.static_map_data_file.exists():
            logger.warning(f"Static map data file not found: {self.static_map_data_file}")
            return None

        try:
            with open(self.static_map_data_file, 'rb') as f:
                compressed_data = f.read()

            # Decompress and unpickle
            decompressed = self._decompressor.decompress(compressed_data)
            static_map_data = pickle.loads(decompressed)

            logger.info("Read static map data from recording")
            return static_map_data
        except Exception as e:
            logger.error(f"Error reading static map data: {e}")
            return None

    def len_game_states(self) -> int:
        counter = 0
        if not self.game_states_file.exists():
            return 0
        with open(self.game_states_file, 'rb') as f:
            while True:
                # Read timestamp (8 bytes)
                timestamp_bytes = f.read(8)
                if not timestamp_bytes:
                    break

                timestamp_ms = int.from_bytes(timestamp_bytes, 'big')

                # Read length (4 bytes)
                length_bytes = f.read(4)
                if not length_bytes:
                    logger.warning(f"Missing length for state at timestamp {timestamp_ms}")
                    break

                length = int.from_bytes(length_bytes, 'big')

                # Seek forward by length bytes
                try:
                    f.seek(length, 1)
                except Exception:
                    # Fall back to reading if seek fails
                    skipped = f.read(length)
                    if len(skipped) != length:
                        logger.warning(f"Incomplete data while skipping at timestamp {timestamp_ms}")
                        break
                counter += 1
        return counter

    def read_game_state(self, index: int) -> Tuple[int, GameState] | None:
        """
        Read game state from the recording.
        """
        if index is not None and index < 0:
            raise ValueError("index must be non-negative")

        game_state = None
        target_idx = index
        current_idx = 0

        with open(self.game_states_file, 'rb') as f:
            while True:
                # Read timestamp (8 bytes)
                timestamp_bytes = f.read(8)
                if not timestamp_bytes:
                    break

                timestamp_ms = int.from_bytes(timestamp_bytes, 'big')

                # Read length (4 bytes)
                length_bytes = f.read(4)
                if not length_bytes:
                    logger.warning(f"Missing length for state at timestamp {timestamp_ms}")
                    break

                length = int.from_bytes(length_bytes, 'big')

                # If we're skipping until the target index, jump the data without decompressing
                if current_idx != target_idx:
                    # Seek forward by length bytes
                    try:
                        f.seek(length, 1)
                    except Exception:
                        # Fall back to reading if seek fails
                        skipped = f.read(length)
                        if len(skipped) != length:
                            logger.warning(f"Incomplete data while skipping at timestamp {timestamp_ms}")
                            break
                    current_idx += 1
                    continue

                # Read compressed data
                compressed_data = f.read(length)
                if len(compressed_data) != length:
                    logger.warning(f"Incomplete data at timestamp {timestamp_ms}")
                    break

                try:
                    # Decompress and unpickle
                    decompressed = self._decompressor.decompress(compressed_data)
                    game_state = pickle.loads(decompressed)
                except Exception as e:
                    logger.error(f"Error decoding game state at index {current_idx} (timestamp {timestamp_ms}): {e}")
                    break

                return timestamp_ms, game_state

        logger.error(f"Game state at index {current_idx} not found")

    def read_json_responses(self) -> List[Tuple[int, dict]]:
        """
        Read all JSON responses from the recording.

        Returns:
            List of (timestamp_ms, json_response) tuples
        """
        json_responses = []

        with open(self.responses_file, 'rb') as f:
            while True:
                # Read timestamp (8 bytes)
                timestamp_bytes = f.read(8)
                if not timestamp_bytes:
                    break

                timestamp_ms = int.from_bytes(timestamp_bytes, 'big')

                # Read length (4 bytes)
                length_bytes = f.read(4)
                if not length_bytes:
                    break

                length = int.from_bytes(length_bytes, 'big')

                # Read compressed data
                compressed_data = f.read(length)
                if len(compressed_data) != length:
                    logger.warning(f"Incomplete JSON data at timestamp {timestamp_ms}")
                    break

                # Decompress and parse JSON
                decompressed = self._decompressor.decompress(compressed_data)
                json_response = json.loads(decompressed.decode('utf-8'))

                json_responses.append((timestamp_ms, json_response))

        logger.info(f"Read {len(json_responses)} JSON responses from recording")
        return json_responses

    def read_json_requests(self) -> List[Tuple[int, dict]]:
        """
        Read all JSON requests from the recording.

        Returns:
            List of (timestamp_ms, request_dict) tuples
        """
        json_requests = []

        with open(self.requests_file, 'rb') as f:
            while True:
                # Read timestamp (8 bytes)
                timestamp_bytes = f.read(8)
                if not timestamp_bytes:
                    break

                timestamp_ms = int.from_bytes(timestamp_bytes, 'big')

                # Read length (4 bytes)
                length_bytes = f.read(4)
                if not length_bytes:
                    break

                length = int.from_bytes(length_bytes, 'big')

                # Read compressed data
                compressed_data = f.read(length)
                if len(compressed_data) != length:
                    logger.warning(f"Incomplete JSON data at timestamp {timestamp_ms}")
                    break

                # Decompress and parse JSON
                decompressed = self._decompressor.decompress(compressed_data)
                json_request = json.loads(decompressed.decode('utf-8'))

                json_requests.append((timestamp_ms, json_request))

        logger.info(f"Read {len(json_requests)} JSON requests from recording")
        return json_requests