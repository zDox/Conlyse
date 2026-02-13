"""
Main server converter logic for processing game responses.
"""
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Tuple, Dict, Any

from conflict_interface.replay.replay_builder import ReplayBuilder
from conflict_interface.data_types.static_map_data import StaticMapData
from tools.server_converter.config import ServerConverterConfig
from tools.server_converter.database import ReplayDatabase, ReplayStatus
from tools.server_converter.redis_consumer import RedisStreamConsumer
from tools.server_converter.storage import HotStorageManager, ColdStorageManager

logger = logging.getLogger(__name__)


class ServerConverter:
    """
    Converts game responses from Redis stream to replay files.
    
    Processes responses in batches, creates/appends to replay files in hot storage,
    and moves completed replays to cold storage.
    """
    
    def __init__(self, config: ServerConverterConfig):
        """
        Initialize the server converter.
        
        Args:
            config: ServerConverterConfig instance
        """
        self.config = config
        
        # Initialize database with PostgreSQL config
        db_config = {
            'host': config.database.host,
            'port': config.database.port,
            'database': config.database.database,
            'user': config.database.user,
            'password': config.database.password
        }
        
        # Initialize components
        self.db = ReplayDatabase(db_config)
        self.db.connect()
        
        self.redis_consumer = RedisStreamConsumer(config.redis)
        self.hot_storage = HotStorageManager(config.storage.hot_storage_dir)
        
        self.cold_storage: Optional[ColdStorageManager] = None
        if config.storage.cold_storage_enabled and config.storage.s3_config:
            self.cold_storage = ColdStorageManager(config.storage.s3_config)
            
        logger.info("Server converter initialized")
        
    def process_batch(self) -> int:
        """
        Process a batch of responses from Redis stream.
        
        Returns:
            Number of responses processed
        """
        # Read messages from Redis using batch_size from redis config
        messages = self.redis_consumer.read_messages(
            count=self.config.redis.batch_size,
            block=self.config.check_interval_seconds * 1000
        )
        
        if not messages:
            logger.debug("No messages to process")
            return 0
            
        logger.info(f"Processing {len(messages)} messages")
        
        # Group messages by game_id and player_id
        grouped_messages: Dict[Tuple[int, int], List[Tuple[str, Dict[str, Any]]]] = {}
        for message_id, message_data in messages:
            game_id = message_data['game_id']
            player_id = message_data['player_id']
            key = (game_id, player_id)
            
            if key not in grouped_messages:
                grouped_messages[key] = []
            grouped_messages[key].append((message_id, message_data))
            
        # Process each group
        processed_message_ids = []
        for (game_id, player_id), group_messages in grouped_messages.items():
            try:
                success = self._process_game_responses(game_id, player_id, group_messages)
                if success:
                    # Mark messages as acknowledged
                    processed_message_ids.extend([msg_id for msg_id, _ in group_messages])
            except Exception as e:
                logger.error(f"Error processing game {game_id}, player {player_id}: {e}", exc_info=True)
                
        # Acknowledge processed messages
        if processed_message_ids:
            self.redis_consumer.acknowledge_messages(processed_message_ids)
            
        return len(processed_message_ids)
        
    def _process_game_responses(self, game_id: int, player_id: int,
                                messages: List[Tuple[str, Dict[str, Any]]]) -> bool:
        """
        Process responses for a specific game and player.
        
        Args:
            game_id: Game ID
            player_id: Player ID
            messages: List of (message_id, message_data) tuples
            
        Returns:
            True if processing was successful
        """
        logger.info(f"Processing {len(messages)} responses for game {game_id}, player {player_id}")
        
        # Convert messages to the format expected by ReplayBuilder
        json_responses = []
        for _, message_data in messages:
            timestamp = message_data['timestamp']
            response = message_data['response']
            json_responses.append((timestamp, response))
            
        # Check if replay exists in hot storage
        replay_path = self.hot_storage.get_replay_path(game_id, player_id)
        replay_exists = replay_path.exists()
        
        # Get or create database entry
        replay_entry = self.db.get_replay_by_game_and_player(game_id, player_id)
        
        if not replay_exists and not replay_entry:
            # Create new replay
            return self._create_new_replay(game_id, player_id, json_responses, replay_path)
        elif replay_exists and replay_entry:
            # Append to existing replay
            return self._append_to_replay(game_id, player_id, json_responses, 
                                         replay_path, replay_entry)
        else:
            # Inconsistent state - log error
            logger.error(f"Inconsistent state for game {game_id}, player {player_id}: "
                        f"replay_exists={replay_exists}, replay_entry={replay_entry is not None}")
            return False
            
    def _create_new_replay(self, game_id: int, player_id: int,
                          json_responses: List[Tuple[int, dict]],
                          replay_path: Path) -> bool:
        """
        Create a new replay file.
        
        Args:
            game_id: Game ID
            player_id: Player ID
            json_responses: List of (timestamp, response) tuples
            replay_path: Path where replay should be created
            
        Returns:
            True if successful
        """
        logger.info(f"Creating new replay for game {game_id}, player {player_id}")
        
        try:
            # Create replay builder
            builder = ReplayBuilder(replay_path, game_id, player_id)
            
            # Create static map data (empty for now - could be loaded from separate source)
            static_map_data = StaticMapData()
            
            # Create the replay
            initial_index = builder.create_replay(json_responses, static_map_data)
            
            # Create database entry
            recording_start_time = datetime.fromtimestamp(json_responses[0][0] / 1000.0)
            replay_name = f"game_{game_id}_player_{player_id}"
            
            self.db.create_replay_entry(
                game_id=game_id,
                player_id=player_id,
                replay_name=replay_name,
                hot_storage_path=str(replay_path),
                recording_start_time=recording_start_time
            )
            
            # Update response count
            replay_entry = self.db.get_replay_by_game_and_player(game_id, player_id)
            self.db.increment_response_count(replay_entry['id'], len(json_responses))
            
            logger.info(f"Created replay at {replay_path} with {len(json_responses)} responses")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create replay: {e}", exc_info=True)
            return False
            
    def _append_to_replay(self, game_id: int, player_id: int,
                         json_responses: List[Tuple[int, dict]],
                         replay_path: Path, replay_entry: Dict[str, Any]) -> bool:
        """
        Append responses to an existing replay.
        
        Args:
            game_id: Game ID
            player_id: Player ID
            json_responses: List of (timestamp, response) tuples
            replay_path: Path to existing replay
            replay_entry: Database entry for the replay
            
        Returns:
            True if successful
        """
        logger.info(f"Appending {len(json_responses)} responses to existing replay")
        
        try:
            # Create replay builder in append mode
            builder = ReplayBuilder(replay_path, game_id, player_id)
            
            # Append responses
            builder.append_json_responses(json_responses)
            
            # Update response count
            self.db.increment_response_count(replay_entry['id'], len(json_responses))
            
            logger.info(f"Appended {len(json_responses)} responses to {replay_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to append to replay: {e}", exc_info=True)
            return False
            
    def mark_replay_completed(self, game_id: int, player_id: int) -> bool:
        """
        Mark a replay as completed and move to cold storage if enabled.
        
        Args:
            game_id: Game ID
            player_id: Player ID
            
        Returns:
            True if successful
        """
        replay_entry = self.db.get_replay_by_game_and_player(game_id, player_id)
        if not replay_entry:
            logger.error(f"No replay entry found for game {game_id}, player {player_id}")
            return False
            
        replay_path = self.hot_storage.get_replay_path(game_id, player_id)
        if not replay_path.exists():
            logger.error(f"Replay file not found: {replay_path}")
            return False
            
        # Update recording end time
        recording_end_time = datetime.now()
        
        # Move to cold storage if enabled
        cold_storage_path = None
        if self.cold_storage:
            logger.info(f"Moving replay to cold storage: game {game_id}, player {player_id}")
            cold_storage_path = self.cold_storage.upload_replay(replay_path, game_id, player_id)
            
            if cold_storage_path:
                # Delete from hot storage after successful upload
                self.hot_storage.delete_replay(game_id, player_id)
                
        # Update database
        status = ReplayStatus.ARCHIVED if cold_storage_path else ReplayStatus.COMPLETED
        self.db.update_replay_status(
            replay_entry['id'],
            status,
            recording_end_time=recording_end_time,
            cold_storage_path=cold_storage_path
        )
        
        logger.info(f"Marked replay as {status.value}: game {game_id}, player {player_id}")
        return True
        
    def run(self, max_iterations: Optional[int] = None):
        """
        Run the server converter main loop.
        
        Args:
            max_iterations: Maximum iterations to run (None = run forever)
        """
        logger.info("Starting server converter main loop")
        
        iteration = 0
        try:
            while max_iterations is None or iteration < max_iterations:
                processed = self.process_batch()
                
                if processed == 0:
                    # Sleep for check interval if no messages were processed
                    time.sleep(self.config.check_interval_seconds)
                    
                iteration += 1
                
        except KeyboardInterrupt:
            logger.info("Received interrupt signal, shutting down...")
        finally:
            self.shutdown()
            
    def shutdown(self):
        """Clean up resources."""
        logger.info("Shutting down server converter")
        
        if self.redis_consumer:
            self.redis_consumer.close()
            
        if self.db:
            self.db.close()
