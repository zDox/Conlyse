"""
Main server converter logic for processing game responses.
"""
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Tuple, Dict, Any

from conflict_interface.replay.replay_builder import ReplayBuilder
from conflict_interface.replay.response_metadata import ResponseMetadata
from server_converter.config import ServerConverterConfig
from server_converter.database import ReplayDatabase, ReplayStatus
from server_converter.redis_consumer import RedisStreamConsumer
from server_converter.cold_storage import ColdStorageManager
from server_converter.hot_storage import HotStorageManager
from server_converter.response_cache import ResponseCache
from server_converter import metrics

logger = logging.getLogger(__name__)


class ServerConverter:
    """
    Converts game responses from Redis stream to replay files.
    
    Caches responses on disk until a game accumulates enough for processing,
    then creates/appends to replay files in hot storage,
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
        
        # Initialize response cache in a subdirectory of hot storage
        cache_dir = config.storage.hot_storage_dir / ".response_cache"
        self.response_cache = ResponseCache(cache_dir, config.redis.batch_size)
        
        self.cold_storage: Optional[ColdStorageManager] = None
        if config.storage.cold_storage_enabled and config.storage.s3_config:
            self.cold_storage = ColdStorageManager(config.storage.s3_config)
            
        logger.info("Server converter initialized with disk-based response caching")
        
    def process_batch(self) -> int:
        """
        Process messages from Redis stream and cache them on disk.
        
        Reads messages from Redis, caches them to disk, then processes
        any games that have accumulated enough responses.
        
        Returns:
            Number of messages processed
        """
        start_time = time.time()
        
        try:
            # Read messages from Redis using batch_size from redis config
            messages = self.redis_consumer.read_messages(
                count=self.config.redis.batch_size
            )
            
            
            if not messages:
                # No new messages, check if any cached games are ready to process
                self._process_ready_games()
                logger.debug("No new messages to cache")
                return 0
                
            logger.info(f"Caching {len(messages)} messages to disk")
            
            # Cache all messages to disk
            cached_message_ids = []
            for message_id, message_data in messages:
                try:
                    # Extract core metadata from the ResponseMetadata payload.
                    meta_dict = message_data["metadata"]
                    response = message_data["response"]

                    metadata = ResponseMetadata.from_dict(meta_dict)

                    # Cache to disk
                    self.response_cache.add_response(metadata, response)
                    cached_message_ids.append(message_id)
                    
                except Exception as e:
                    logger.error(f"Error caching message {message_id} (game {message_data.get('game_id')}, "
                               f"player {message_data.get('player_id')}): {e}", exc_info=True)
                    metrics.errors_total.labels(error_type='caching').inc()
                    # Message not added to cached_message_ids, will remain in Redis for retry
                    
            # Acknowledge cached messages
            if cached_message_ids:
                self.redis_consumer.acknowledge_messages(cached_message_ids)
                logger.info(f"Cached and acknowledged {len(cached_message_ids)} messages")
                
            # Process any games that now have enough responses
            self._process_ready_games()
            
            return len(cached_message_ids)
            
        finally:
            # Record processing duration
            duration = time.time() - start_time
            metrics.messages_processing_duration_seconds.observe(duration)
        
    def _process_ready_games(self):
        """
        Process games that have accumulated enough responses in the cache.
        
        Checks the cache for games with at least batch_size responses and
        processes them into replay files.
        """
        ready_games = self.response_cache.list_games_ready_to_process()
        
        if not ready_games:
            return
            
        logger.info(f"Found {len(ready_games)} games ready to process")
        
        for game_id, player_id in ready_games:
            try:
                # Get all cached responses for this game
                cached_responses = self.response_cache.get_cached_responses(game_id, player_id)
                
                # Note: There's a potential TOCTOU race between list_games_ready_to_process()
                # and this check. In distributed deployments with multiple converter instances,
                # another instance might process and clear the cache. This is expected behavior
                # and handled gracefully by skipping if responses are insufficient.
                if len(cached_responses) < self.config.redis.batch_size:
                    # Race condition - responses were removed by another process
                    logger.debug(f"Skipping game {game_id}, player {player_id}: "
                               f"only {len(cached_responses)} responses available")
                    continue
                    
                logger.info(f"Processing {len(cached_responses)} cached responses for game {game_id}, player {player_id}")
                
                # Process the responses
                success = self._process_game_responses(game_id, player_id, cached_responses)
                
                if success:
                    # Clear the cache on success
                    self.response_cache.clear_cache(game_id, player_id)
                    metrics.messages_processed_total.labels(status='success').inc(len(cached_responses))
                    logger.info(f"Successfully processed and cleared cache for game {game_id}, player {player_id}")
                else:
                    metrics.messages_processed_total.labels(status='error').inc(len(cached_responses))
                    # Keep cache on failure for retry
                    logger.warning(f"Failed to process game {game_id}, player {player_id}, keeping cache for retry")
                    
            except Exception as e:
                logger.error(f"Error processing ready game {game_id}, player {player_id}: {e}", exc_info=True)
                metrics.errors_total.labels(error_type='processing').inc()
        
    def _process_game_responses(self, game_id: int, player_id: int,
                                json_responses: List[Tuple[ResponseMetadata, dict]]) -> bool:
        """
        Process responses for a specific game and player.
        
        Args:
            game_id: Game ID
            player_id: Player ID
            json_responses: List of (timestamp, response) tuples
            
        Returns:
            True if processing was successful
        """
        logger.info(f"Processing {len(json_responses)} responses for game {game_id}, player {player_id}")
        
        # Check if replay exists in hot storage using cache
        replay_exists = self.hot_storage.replay_exists(game_id, player_id)

        # Get or create database entry
        replay_entry = self.db.get_replay_by_game_and_player(game_id, player_id)
        
        if not replay_exists and not replay_entry:
            # Create new replay
            return self._create_new_replay(game_id, player_id, json_responses)
        elif replay_exists and replay_entry:
            # Append to existing replay
            return self._append_to_replay(game_id, player_id, json_responses, replay_entry)
        else:
            # Inconsistent state - log error
            logger.error(f"Inconsistent state for game {game_id}, player {player_id}: "
                        f"replay_exists={replay_exists}, replay_entry={replay_entry is not None}")
            return False
            
    def _create_new_replay(self, game_id: int, player_id: int,
                          json_responses: List[Tuple[ResponseMetadata, dict]]) -> bool:
        """
        Create a new replay file.
        
        Args:
            game_id: Game ID
            player_id: Player ID
            json_responses: List of (timestamp, response) tuples

        Returns:
            True if successful
        """
        logger.info(f"Creating new replay for game {game_id}, player {player_id}")
        
        start_time = time.time()
        
        try:
            # Register replay in hot storage cache and get path
            replay_path = self.hot_storage.add_replay(game_id, player_id)

            # Create replay builder
            builder = ReplayBuilder(replay_path, game_id, player_id)
            builder.setup_parsers()
            
            # Static map data is intentionally never included in server converter replays
            static_map_data = None

            # Create the replay
            initial_index = builder.create_replay(json_responses, static_map_data)
            remaining_responses = json_responses[initial_index + 1:] if initial_index + 1 < len(json_responses) else []
            builder.append_json_responses(remaining_responses)

            # Create database entry
            # recording_start_time is based on the first response metadata timestamp (ms)
            first_meta = json_responses[0][0]
            recording_start_time = datetime.fromtimestamp(first_meta.timestamp / 1000.0)
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

            # Optionally mirror the replay to cold storage after creating it.
            if self.cold_storage and self.config.storage.always_update_cold_storage:
                logger.info(
                    "Uploading new replay snapshot to cold storage: "
                    f"game {game_id}, player {player_id}"
                )
                try:
                    s3_key = self.cold_storage.upload_replay(
                        replay_path, game_id, player_id
                    )
                    if s3_key:
                        # Keep status as RECORDING but store/update S3 key.
                        self.db.update_replay_status(
                            replay_entry["id"],
                            ReplayStatus.RECORDING,
                            s3_key=s3_key,
                        )
                        metrics.cold_storage_uploads_total.labels(status='success').inc()
                    else:
                        metrics.cold_storage_uploads_total.labels(status='error').inc()
                        metrics.errors_total.labels(error_type='storage').inc()
                except Exception as e:
                    logger.error(
                        f"Failed to upload new replay snapshot to cold storage: {e}",
                        exc_info=True,
                    )
                    metrics.cold_storage_uploads_total.labels(status='error').inc()
                    metrics.errors_total.labels(error_type='storage').inc()
            
            # Update metrics
            metrics.responses_per_replay_summary.observe(len(json_responses))
            metrics.replay_operations_total.labels(operation='create', status='success').inc()
            metrics.hot_storage_replays.inc()
            
            logger.info(f"Created replay at {replay_path} with {len(json_responses)} responses")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create replay: {e}", exc_info=True)
            metrics.replay_operations_total.labels(operation='create', status='error').inc()
            metrics.errors_total.labels(error_type='storage').inc()
            return False
            
        finally:
            duration = time.time() - start_time
            metrics.replay_creation_duration_seconds.observe(duration)
            
    def _append_to_replay(self, game_id: int, player_id: int,
                         json_responses: List[Tuple[ResponseMetadata, dict]],
                         replay_entry: Dict[str, Any]) -> bool:
        """
        Append responses to an existing replay.
        
        Args:
            game_id: Game ID
            player_id: Player ID
            json_responses: List of (timestamp, response) tuples
            replay_entry: Database entry for the replay
            
        Returns:
            True if successful
        """
        logger.info(f"Appending {len(json_responses)} responses to existing replay")
        
        start_time = time.time()
        
        try:
            # Get replay path from hot storage
            replay_path = self.hot_storage.get_replay_path(game_id, player_id)
            # Create replay builder in append mode
            builder = ReplayBuilder(replay_path, game_id, player_id)
            builder.setup_parsers()
            
            # Append responses
            builder.append_json_responses(json_responses)
            
            # Update response count
            self.db.increment_response_count(replay_entry['id'], len(json_responses))
            
            # Optionally mirror the updated replay to cold storage after appending.
            if self.cold_storage and self.config.storage.always_update_cold_storage:
                logger.info(
                    "Uploading updated replay snapshot to cold storage: "
                    f"game {game_id}, player {player_id}"
                )
                try:
                    s3_key = self.cold_storage.upload_replay(
                        replay_path, game_id, player_id
                    )
                    if s3_key:
                        # Keep status as RECORDING but store/update S3 key.
                        self.db.update_replay_status(
                            replay_entry["id"],
                            ReplayStatus.RECORDING,
                            s3_key=s3_key,
                        )
                        metrics.cold_storage_uploads_total.labels(status='success').inc()
                    else:
                        metrics.cold_storage_uploads_total.labels(status='error').inc()
                        metrics.errors_total.labels(error_type='storage').inc()
                except Exception as e:
                    logger.error(
                        f"Failed to upload updated replay snapshot to cold storage: {e}",
                        exc_info=True,
                    )
                    metrics.cold_storage_uploads_total.labels(status='error').inc()
                    metrics.errors_total.labels(error_type='storage').inc()

            # Update metrics
            metrics.responses_per_replay_summary.observe(len(json_responses))
            metrics.replay_operations_total.labels(operation='append', status='success').inc()
            
            logger.info(f"Appended {len(json_responses)} responses to {replay_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to append to replay: {e}", exc_info=True)
            metrics.replay_operations_total.labels(operation='append', status='error').inc()
            metrics.errors_total.labels(error_type='storage').inc()
            return False
            
        finally:
            duration = time.time() - start_time
            metrics.replay_append_duration_seconds.observe(duration)
            
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
            metrics.replay_operations_total.labels(operation='complete', status='error').inc()
            return False
            
        replay_path = self.hot_storage.get_replay_path(game_id, player_id)
        if not replay_path.exists():
            logger.error(f"Replay file not found: {replay_path}")
            metrics.replay_operations_total.labels(operation='complete', status='error').inc()
            return False
            
        # Update recording end time
        recording_end_time = datetime.now()

        # Move to cold storage if enabled
        s3_key = None
        if self.cold_storage:
            logger.info(f"Moving replay to cold storage: game {game_id}, player {player_id}")
            try:
                s3_key = self.cold_storage.upload_replay(
                    replay_path, game_id, player_id
                )

                if s3_key:
                    # Delete from hot storage after successful upload
                    self.hot_storage.delete_replay(game_id, player_id)
                    metrics.hot_storage_replays.dec()
                    metrics.cold_storage_uploads_total.labels(status="success").inc()
                else:
                    metrics.cold_storage_uploads_total.labels(status="error").inc()
                    metrics.errors_total.labels(error_type="storage").inc()

            except Exception as e:
                logger.error(f"Failed to upload to cold storage: {e}", exc_info=True)
                metrics.cold_storage_uploads_total.labels(status='error').inc()
                metrics.errors_total.labels(error_type='storage').inc()

        # Update database
        status = ReplayStatus.ARCHIVED if s3_key else ReplayStatus.COMPLETED
        self.db.update_replay_status(
            replay_entry["id"],
            status,
            recording_end_time=recording_end_time,
            s3_key=s3_key,
        )

        try:
            self.db.remove_game_from_recording_lists(game_id)
        except Exception as e:
            logger.warning(
                f"Failed to remove game {game_id} from recording lists: {e}",
                exc_info=True,
            )

        metrics.replay_operations_total.labels(operation='complete', status='success').inc()
        logger.info(f"Marked replay as {status.value}: game {game_id}, player {player_id}")
        return True
        
    def run(self):
        """
        Run the server converter main loop.
        """
        logger.info("Starting server converter main loop")
        
        try:
            while True:
                # Update hot storage gauge
                self._update_hot_storage_metric()
                
                # process_batch() is expected to perform a blocking read with the
                # configured timeout, so no additional sleep is needed here.
                self.process_batch()

        except KeyboardInterrupt:
            logger.info("Received interrupt signal, shutting down...")
        finally:
            self.shutdown()
            
    def _update_hot_storage_metric(self):
        """Update the hot storage replays gauge metric using cached count."""
        try:
            replay_count = self.hot_storage.count_replays()
            metrics.hot_storage_replays.set(replay_count)
        except Exception as e:
            logger.warning(f"Failed to update hot storage metric: {e}")
            
    def shutdown(self):
        """Clean up resources."""
        logger.info("Shutting down server converter")

        if self.redis_consumer:
            self.redis_consumer.close()
            
        if self.db:
            self.db.close()
