"""
Disk-based cache for game responses.

Stores responses on disk temporarily until they can be processed into replays.
"""
import json
import logging
from pathlib import Path
from typing import List, Tuple, Dict, Optional
import fcntl
import tempfile

logger = logging.getLogger(__name__)


class ResponseCache:
    """
    Disk-based cache for game responses.
    
    Stores incoming responses on disk and tracks count per game/player.
    Only processes games once they reach the configured batch size threshold.
    """
    
    def __init__(self, cache_dir: Path, batch_size: int = 10):
        """
        Initialize the response cache.
        
        Args:
            cache_dir: Directory to store cached responses
            batch_size: Minimum number of responses before processing
        """
        self.cache_dir = Path(cache_dir)
        self.batch_size = batch_size
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Response cache initialized at {self.cache_dir}, batch_size={batch_size}")
        
    def _get_cache_file(self, game_id: int, player_id: int) -> Path:
        """Get the cache file path for a game/player combination."""
        return self.cache_dir / f"game_{game_id}_player_{player_id}.jsonl"
    
    def _get_lock_file(self, game_id: int, player_id: int) -> Path:
        """Get the lock file path for a game/player combination."""
        return self.cache_dir / f"game_{game_id}_player_{player_id}.lock"
        
    def add_response(self, game_id: int, player_id: int, timestamp: int, response: dict):
        """
        Add a response to the cache.
        
        Args:
            game_id: Game ID
            player_id: Player ID
            timestamp: Unix timestamp in milliseconds
            response: Response JSON dict
        """
        cache_file = self._get_cache_file(game_id, player_id)
        lock_file = self._get_lock_file(game_id, player_id)
        
        # Use file locking to prevent race conditions
        with open(lock_file, 'w') as lock:
            try:
                fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
                
                # Append response to cache file (one JSON per line)
                with open(cache_file, 'a') as f:
                    entry = {
                        'timestamp': timestamp,
                        'response': response
                    }
                    f.write(json.dumps(entry) + '\n')
                    
                logger.debug(f"Cached response for game {game_id}, player {player_id}")
                
            finally:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
                
    def get_response_count(self, game_id: int, player_id: int) -> int:
        """
        Get the number of cached responses for a game/player.
        
        Args:
            game_id: Game ID
            player_id: Player ID
            
        Returns:
            Number of cached responses
        """
        cache_file = self._get_cache_file(game_id, player_id)
        
        if not cache_file.exists():
            return 0
            
        lock_file = self._get_lock_file(game_id, player_id)
        
        with open(lock_file, 'w') as lock:
            try:
                fcntl.flock(lock.fileno(), fcntl.LOCK_SH)  # Shared lock for reading
                
                count = 0
                with open(cache_file, 'r') as f:
                    for _ in f:
                        count += 1
                        
                return count
                
            finally:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
                
    def has_enough_responses(self, game_id: int, player_id: int) -> bool:
        """
        Check if a game/player has enough cached responses to process.
        
        Args:
            game_id: Game ID
            player_id: Player ID
            
        Returns:
            True if response count >= batch_size
        """
        return self.get_response_count(game_id, player_id) >= self.batch_size
        
    def get_cached_responses(self, game_id: int, player_id: int) -> List[Tuple[int, dict]]:
        """
        Get all cached responses for a game/player.
        
        Args:
            game_id: Game ID
            player_id: Player ID
            
        Returns:
            List of (timestamp, response) tuples
        """
        cache_file = self._get_cache_file(game_id, player_id)
        
        if not cache_file.exists():
            return []
            
        lock_file = self._get_lock_file(game_id, player_id)
        
        with open(lock_file, 'w') as lock:
            try:
                fcntl.flock(lock.fileno(), fcntl.LOCK_SH)  # Shared lock for reading
                
                responses = []
                with open(cache_file, 'r') as f:
                    for line in f:
                        if line.strip():
                            entry = json.loads(line)
                            responses.append((entry['timestamp'], entry['response']))
                            
                return responses
                
            finally:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
                
    def clear_cache(self, game_id: int, player_id: int):
        """
        Clear cached responses for a game/player after successful processing.
        
        Args:
            game_id: Game ID
            player_id: Player ID
        """
        cache_file = self._get_cache_file(game_id, player_id)
        lock_file = self._get_lock_file(game_id, player_id)
        
        with open(lock_file, 'w') as lock:
            try:
                fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
                
                if cache_file.exists():
                    cache_file.unlink()
                    logger.debug(f"Cleared cache for game {game_id}, player {player_id}")
                    
            finally:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
                
        # Clean up lock file
        if lock_file.exists():
            lock_file.unlink()
            
    def list_games_with_responses(self) -> List[Tuple[int, int]]:
        """
        List all game/player combinations that have cached responses.
        
        Returns:
            List of (game_id, player_id) tuples
        """
        games = []
        
        for cache_file in self.cache_dir.glob("game_*_player_*.jsonl"):
            # Parse filename: game_<id>_player_<id>.jsonl
            parts = cache_file.stem.split('_')
            if len(parts) == 4 and parts[0] == 'game' and parts[2] == 'player':
                try:
                    game_id = int(parts[1])
                    player_id = int(parts[3])
                    games.append((game_id, player_id))
                except ValueError:
                    logger.warning(f"Invalid cache filename: {cache_file.name}")
                    
        return games
        
    def list_games_ready_to_process(self) -> List[Tuple[int, int]]:
        """
        List all game/player combinations that have enough responses to process.
        
        Returns:
            List of (game_id, player_id) tuples with count >= batch_size
        """
        ready_games = []
        
        for game_id, player_id in self.list_games_with_responses():
            if self.has_enough_responses(game_id, player_id):
                ready_games.append((game_id, player_id))
                
        return ready_games
        
    def get_cache_stats(self) -> Dict[str, int]:
        """
        Get statistics about the cache.
        
        Returns:
            Dictionary with cache statistics
        """
        games = self.list_games_with_responses()
        total_responses = 0
        ready_count = 0
        
        for game_id, player_id in games:
            count = self.get_response_count(game_id, player_id)
            total_responses += count
            if count >= self.batch_size:
                ready_count += 1
                
        return {
            'total_games': len(games),
            'games_ready': ready_count,
            'total_responses': total_responses
        }
