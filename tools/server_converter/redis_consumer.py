"""
Redis stream consumer for processing game responses.
"""
import json
import logging
from typing import List, Tuple, Optional, Dict, Any

try:
    import zstandard as zstd
    ZSTD_AVAILABLE = True
except ImportError:
    ZSTD_AVAILABLE = False
    logging.warning(
        "zstandard package not available. Compressed responses will not be supported. "
        "Install it with: pip install zstandard"
    )

logger = logging.getLogger(__name__)


class RedisStreamConsumer:
    """Consumes messages from a Redis stream."""
    
    def __init__(self, redis_config):
        """
        Initialize the Redis consumer.
        
        Args:
            redis_config: RedisConfig instance with connection details
        """
        try:
            import redis
        except ImportError:
            raise ImportError(
                "redis package is required for RedisStreamConsumer. "
                "Install it with: pip install redis"
            )
        
        self.config = redis_config
        self.redis_client = redis.Redis(
            host=redis_config.host,
            port=redis_config.port,
            db=redis_config.db,
            password=redis_config.password,
            decode_responses=False  # We'll handle decoding manually
        )
        
        # Create decompressor for reuse across messages
        self.decompressor = zstd.ZstdDecompressor() if ZSTD_AVAILABLE else None
        
        # Create consumer group if it doesn't exist
        self._ensure_consumer_group()
        
    def _ensure_consumer_group(self):
        """Create the consumer group if it doesn't exist."""
        try:
            self.redis_client.xgroup_create(
                name=self.config.stream_name,
                groupname=self.config.consumer_group,
                id='0',
                mkstream=True
            )
            logger.info(f"Created consumer group: {self.config.consumer_group}")
        except Exception as e:
            # Group already exists or stream doesn't exist yet
            if "BUSYGROUP" not in str(e):
                logger.debug(f"Consumer group creation: {e}")
                
    def read_messages(self, count: Optional[int] = None, 
                     block: Optional[int] = None) -> List[Tuple[str, Dict[str, Any]]]:
        """
        Read messages from the Redis stream.
        
        Args:
            count: Maximum number of messages to read (uses config.batch_size if None)
            block: Time to block in milliseconds (None = don't block)
            
        Returns:
            List of (message_id, message_data) tuples where message_data contains:
                - timestamp: Unix timestamp in milliseconds
                - game_id: Game ID
                - player_id: Player ID
                - response: JSON response dict
        """
        if count is None:
            count = self.config.batch_size
            
        try:
            # Read from consumer group
            messages = self.redis_client.xreadgroup(
                groupname=self.config.consumer_group,
                consumername=self.config.consumer_name,
                streams={self.config.stream_name: '>'},
                count=count,
                block=block
            )
            
            result = []
            if messages:
                for stream_name, stream_messages in messages:
                    for message_id, message_data in stream_messages:
                        # Decode the message data
                        decoded_data = {}
                        for key, value in message_data.items():
                            key_str = key.decode('utf-8') if isinstance(key, bytes) else key
                            
                            # Parse based on key
                            if key_str == 'response':
                                # Response might be compressed binary or uncompressed JSON string
                                if isinstance(value, bytes):
                                    # Try to decompress first (new format)
                                    try:
                                        if self.decompressor:
                                            decompressed = self.decompressor.decompress(value)
                                            value_str = decompressed.decode('utf-8')
                                        else:
                                            # Fall back to treating as uncompressed
                                            value_str = value.decode('utf-8')
                                    except Exception as e:
                                        # If decompression fails, treat as uncompressed (backward compatibility)
                                        game_id = decoded_data.get('game_id', 'unknown')
                                        player_id = decoded_data.get('player_id', 'unknown')
                                        logger.debug(
                                            f"Decompression failed for game_id={game_id}, player_id={player_id}: {e}"
                                        )
                                        value_str = value.decode('utf-8')
                                else:
                                    value_str = value
                                    
                                decoded_data[key_str] = json.loads(value_str)
                            else:
                                # Other fields (timestamp, game_id, player_id) are simple values
                                value_str = value.decode('utf-8') if isinstance(value, bytes) else value
                                # Try to convert to int if it's a numeric field
                                if key_str in ('timestamp', 'game_id', 'player_id'):
                                    decoded_data[key_str] = int(value_str)
                                else:
                                    decoded_data[key_str] = value_str
                        
                        message_id_str = message_id.decode('utf-8') if isinstance(message_id, bytes) else message_id
                        result.append((message_id_str, decoded_data))
                        
            return result
            
        except Exception as e:
            logger.error(f"Error reading from Redis stream: {e}")
            return []
            
    def acknowledge_messages(self, message_ids: List[str]):
        """
        Acknowledge that messages have been processed.
        
        Args:
            message_ids: List of message IDs to acknowledge
        """
        if not message_ids:
            return
            
        try:
            self.redis_client.xack(
                self.config.stream_name,
                self.config.consumer_group,
                *message_ids
            )
            logger.debug(f"Acknowledged {len(message_ids)} messages")
        except Exception as e:
            logger.error(f"Error acknowledging messages: {e}")
            
    def get_pending_messages(self) -> int:
        """
        Get the count of pending (unacknowledged) messages.
        
        Returns:
            Number of pending messages
        """
        try:
            pending = self.redis_client.xpending(
                self.config.stream_name,
                self.config.consumer_group
            )
            return pending['pending'] if pending else 0
        except Exception as e:
            logger.error(f"Error getting pending messages: {e}")
            return 0
            
    def close(self):
        """Close the Redis connection."""
        if self.redis_client:
            self.redis_client.close()
