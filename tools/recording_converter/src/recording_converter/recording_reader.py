from __future__ import annotations

import json
import os
import pickle
from pathlib import Path
from typing import List
from typing import Optional
from typing import TYPE_CHECKING
from typing import Tuple

import orjson
import zstandard as zstd
from tqdm import tqdm

from conflict_interface.replay.response_metadata import ResponseMetadata
from recorder_logger import get_logger

if TYPE_CHECKING:
    from conflict_interface.data_types.newest.game_state.game_state import GameState

logger = get_logger()

class RecordingReader:
    def __init__(self, recording_dir: Path, static_map_data_deprecated = None, use_tqdm: bool = True):
        self.recording_dir = Path(recording_dir)
        self.game_states_file = self.recording_dir / "game_states.bin"
        self.requests_file = self.recording_dir / "requests.jsonl.zst"
        self.responses_file = self.recording_dir / "responses.jsonl.zst"

        self.metadata_file = self.recording_dir / "metadata.json"

        self.metadata = None
        self._decompressor = zstd.ZstdDecompressor()
        # Controls whether tqdm progress bars are shown from this reader.
        # In multiprocessing workers we typically disable tqdm to avoid garbled output.
        self._use_tqdm = use_tqdm

    def read_metadata(self) -> Optional[dict]:
        """
        Read metadata from the recording.

        Returns:
            Metadata dictionary or None if not found
        """
        if not self.metadata_file.exists():
            logger.warning(f"Metadata file not found: {self.metadata_file}")
            return None

        try:
            with open(self.metadata_file, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            logger.info("Read metadata from recording")
            return metadata
        except Exception as e:
            logger.error(f"Error reading metadata: {e}")
            return None

    def get_metadata(self) -> dict:
        """
        Get metadata, reading from file if not already loaded.

        Returns:
            Metadata dictionary
        """
        if self.metadata is None:
            self.metadata = self.read_metadata()
            if self.metadata is None:
                self.metadata = {}
        return self.metadata


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


    def len_updates(self) -> int:
        metadata = self.get_metadata()
        updates = metadata.get('updates', None)
        if updates is None:
            return 0
        return len(updates)

    def read_json_response_file(self, file):
        """
        Read a single responses_XXXX.jsonl.zst file and return a list of
        (ResponseMetadata, response_dict) tuples.
        """
        json_responses: List[Tuple[ResponseMetadata, dict]] = []
        with open(self.recording_dir/file, 'rb') as f:
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

                # Decompress and parse inner payload.
                decompressed = self._decompressor.decompress(compressed_data)

                # format: [4 bytes BE metadata_len][metadata JSON][4 bytes BE response_len][response JSON]
                try:
                    meta_len = int.from_bytes(decompressed[0:4], "big")
                    resp_offset = 4 + meta_len
                    if meta_len > 0 and resp_offset + 4 <= len(decompressed):
                        resp_len = int.from_bytes(
                            decompressed[resp_offset:resp_offset + 4],
                            "big",
                        )
                        meta_start = 4
                        meta_end = meta_start + meta_len
                        resp_start = resp_offset + 4
                        resp_end = resp_start + resp_len

                        if resp_end <= len(decompressed):
                            meta_bytes = decompressed[meta_start:meta_end]
                            resp_bytes = decompressed[resp_start:resp_end]

                            metadata = ResponseMetadata.from_string(
                                meta_bytes.decode("utf-8")
                            )
                            json_response = orjson.loads(resp_bytes)

                            # Prefer the inner timestamp if present; otherwise, keep outer.
                            if metadata.timestamp == 0:
                                metadata.timestamp = int(timestamp_ms)

                            json_responses.append((metadata, json_response))
                            continue
                except Exception as exc:
                    logger.warning(
                        f"Failed to parse response frame at timestamp {timestamp_ms}: {exc}"
                    )

        return json_responses

    def read_json_responses(self, limit: int = None) -> List[Tuple[ResponseMetadata, dict]]:
        """
        Read all JSON responses from the recording.

        Returns:
            List of (ResponseMetadata, json_response) tuples
        """
        json_responses: List[Tuple[ResponseMetadata, dict]] = []
        len_updates = self.len_updates()
        number_of_responses_to_process = len_updates if limit is None else min(limit, len_updates)
        response_files = []
        for file in os.listdir(self.recording_dir):
            if file.startswith("responses"):
                response_files.append(file)
        # Response files have the name responses_0001.jsonl.zst, responses_0002.jsonl.zst, etc.
        logger.info(f"Found {len(response_files)} response files in recording")
        response_files.sort()
        for file in response_files:
            logger.info(f"Reading responses from {file}")
            json_responses += self.read_json_response_file(file)

        return json_responses[0:limit]

    def read_json_requests(self, limit: int = None) -> List[Tuple[int, dict]]:
        """
        Read all JSON requests from the recording.

        Returns:
            List of (timestamp_ms, request_dict) tuples
        """
        json_requests = []

        len_updates =  self.len_updates()
        number_of_requests_to_process = len_updates if limit is None else min(limit, len_updates)
        with open(self.requests_file, 'rb') as f:
            iterator = range(number_of_requests_to_process)
            if self._use_tqdm:
                iterator = tqdm(
                    iterator,
                    desc="Reading JSON requests: ",
                    unit="Request",
                    unit_scale=True,
                )
            for _ in iterator:
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

