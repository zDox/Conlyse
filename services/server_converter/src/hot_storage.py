import logging
import os
from pathlib import Path
from typing import Set
from typing import Tuple

logger = logging.getLogger(__name__)


class HotStorageManager:
    """Manages replay files in hot (local) storage with efficient caching."""

    def __init__(self, hot_storage_dir: Path):
        """
        Initialize hot storage manager with file cache.

        Args:
            hot_storage_dir: Directory for hot storage
        """
        self.hot_storage_dir = hot_storage_dir
        self.hot_storage_dir.mkdir(parents=True, exist_ok=True)

        # Cache of (game_id, player_id) tuples for O(1) lookups
        self._replay_cache: Set[Tuple[int, int]] = set()
        self._cache_initialized = False

        # Initialize cache by scanning directory
        self._initialize_cache()

    def _initialize_cache(self):
        """
        Initialize the replay cache by scanning the hot storage directory.
        Uses efficient os.scandir for better performance with large directories.
        """
        if self._cache_initialized:
            return

        logger.info(f"Initializing replay cache from {self.hot_storage_dir}")
        count = 0

        try:
            with os.scandir(self.hot_storage_dir) as entries:
                for entry in entries:
                    if entry.is_file() and entry.name.startswith('game_') and entry.name.endswith('.bin'):
                        # Parse filename: game_{game_id}_player_{player_id}.bin
                        try:
                            parts = entry.name[5:-4].split('_player_')  # Remove 'game_' prefix and '.bin' suffix
                            if len(parts) == 2:
                                game_id = int(parts[0])
                                player_id = int(parts[1])
                                self._replay_cache.add((game_id, player_id))
                                count += 1
                        except (ValueError, IndexError) as e:
                            logger.warning(f"Could not parse replay filename: {entry.name}")

            self._cache_initialized = True
            logger.info(f"Replay cache initialized with {count} replays")

        except Exception as e:
            logger.error(f"Error initializing replay cache: {e}")
            self._cache_initialized = False

    def get_replay_path(self, game_id: int, player_id: int) -> Path:
        """
        Get the path where a replay should be stored.

        Args:
            game_id: Game ID
            player_id: Player ID

        Returns:
            Path to the replay file
        """
        return self.hot_storage_dir / f"game_{game_id}_player_{player_id}.bin"

    def replay_exists(self, game_id: int, player_id: int) -> bool:
        """
        Check if a replay file exists in hot storage.
        Uses cached set for O(1) lookup performance.

        Args:
            game_id: Game ID
            player_id: Player ID

        Returns:
            True if replay file exists
        """
        return (game_id, player_id) in self._replay_cache

    def add_replay(self, game_id: int, player_id: int) -> Path:
        """
        Register a new replay file in hot storage.
        This should be called when a replay file is created to maintain cache consistency.

        Args:
            game_id: Game ID
            player_id: Player ID

        Returns:
            Path to the replay file
        """
        replay_path = self.get_replay_path(game_id, player_id)
        self._replay_cache.add((game_id, player_id))
        logger.debug(f"Added replay to cache: game {game_id}, player {player_id}")
        return replay_path

    def delete_replay(self, game_id: int, player_id: int) -> bool:
        """
        Delete a replay file from hot storage.

        Args:
            game_id: Game ID
            player_id: Player ID

        Returns:
            True if file was deleted, False if it didn't exist
        """
        replay_path = self.get_replay_path(game_id, player_id)
        if replay_path.exists():
            replay_path.unlink()
            self._replay_cache.discard((game_id, player_id))

            logger.info(f"Deleted replay from hot storage: {replay_path}")
            return True
        return False

    def list_replays(self):
        """
        List all replay files in hot storage.

        Returns:
            Iterator of Path objects for each replay file
        """
        return self.hot_storage_dir.glob("game_*_player_*.bin")

    def count_replays(self) -> int:
        """
        Count the number of replay files in hot storage.
        Uses cache for O(1) performance.

        Returns:
            Number of replay files
        """
        return len(self._replay_cache)
