from __future__ import annotations

import pickle
import threading
from pathlib import Path
from typing import Optional
from typing import Set

import zstandard as zstd

from tools.server_observer.recorder_logger import get_logger

logger = get_logger()


class StaticMapCache:
    """
    Cache static map data per map_id to avoid duplicate downloads.
    """

    def __init__(self, cache_dir: Path):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._saved_ids: Set[int] = set()
        self._lock = threading.Lock()
        self._compressor = zstd.ZstdCompressor(level=3)

        for file in self.cache_dir.glob("map_*.bin"):
            try:
                map_id = int(file.stem.replace("map_", ""))
                self._saved_ids.add(map_id)
            except ValueError:
                continue

    def is_cached(self, map_id: int) -> bool:
        return map_id in self._saved_ids

    def save(self, map_id: Optional[int], static_map_data) -> Optional[Path]:
        if map_id is None or static_map_data is None:
            return None
        with self._lock:
            path = self.cache_dir / f"map_{map_id}.bin"
            if map_id in self._saved_ids and path.exists():
                return path
            try:
                data = pickle.dumps(static_map_data)
                compressed = self._compressor.compress(data)
                with path.open("wb") as f:
                    f.write(compressed)
                self._saved_ids.add(map_id)
                logger.info(f"Cached static map data for map_id {map_id} at {path}")
                return path
            except Exception as exc:
                logger.warning(f"Failed to cache static map data for map_id {map_id}: {exc}")
                return None
