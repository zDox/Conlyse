"""
Redis stream consumer for processing game responses.
"""
import json
import logging
from typing import List, Tuple, Optional, Dict, Any

try:
    import zstandard as zstd
except ImportError:
    raise ImportError(
        "zstandard package is required for RedisStreamConsumer. "
        "Install it with: pip install zstandard"
    )

logger = logging.getLogger(__name__)


class RedisStreamConsumer:
    """Consumes messages from a Redis stream.

    Wire format (produced by server_observer):
        - ``metadata``: JSON string of ResponseMetadata
            {
                \"timestamp\": <int>,
                \"game_id\": <int>,
                \"player_id\": <int>,
                \"client_version\": <int>,
                \"map_id\": <str>
            }
        - ``response``: zstd-compressed JSON response body
    """
    
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

        # Create decompressor for reuse across messages (responses are always compressed)
        self.decompressor = zstd.ZstdDecompressor()
        # Upper bound for a single decompressed response payload (bytes).
        # Needed because some zstd frames produced by the publisher do not
        # include a content size in the frame header.
        self.max_response_size = 100 * 1024 * 1024
        
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
                
    def read_messages(
        self,
        count: Optional[int] = None,
        block: Optional[int] = None,
    ) -> List[Tuple[str, Dict[str, Any]]]:
        """
        Read messages from the Redis stream.
        
        Args:
            count: Maximum number of messages to read (None = let Redis decide / read as much as possible)
            block: Time to block in milliseconds (None = don't block)
            
        Returns:
            List of (message_id, message_data) tuples where message_data contains:
                - metadata: dict with keys ``timestamp``, ``game_id``, ``player_id``,
                  ``client_version``, and ``map_id`` (string)
                - response: JSON response dict
        """
        try:
            # Read from consumer group
            kwargs = {
                "groupname": self.config.consumer_group,
                "consumername": self.config.consumer_name,
                "streams": {self.config.stream_name: ">"},
                "block": block,
            }
            if count is not None:
                kwargs["count"] = count

            messages = self.redis_client.xreadgroup(**kwargs)
            
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
                                # Response is always compressed binary data
                                if not isinstance(value, bytes):
                                    raise ValueError(
                                        f"Expected compressed bytes for response field, got {type(value)}"
                                    )

                                # Decompress the response. Some frames produced by the
                                # publisher may not include a content size in the frame
                                # header, so we must provide an explicit upper bound.
                                decompressed = self.decompressor.decompress(
                                    value,
                                    max_output_size=self.max_response_size,
                                )
                                value_str = decompressed.decode('utf-8')
                                decoded_data[key_str] = json.loads(value_str)
                            elif key_str == 'metadata':
                                # Metadata is a JSON string containing primitive fields.
                                value_str = value.decode('utf-8') if isinstance(value, bytes) else value
                                meta = json.loads(value_str)
                                if not isinstance(meta, dict):
                                    raise ValueError("metadata field must decode to a JSON object")

                                # Normalize and coerce expected integer fields.
                                normalized = {}
                                for field in ('timestamp', 'game_id', 'player_id', 'client_version'):
                                    if field not in meta:
                                        raise KeyError(f"Missing '{field}' in metadata")
                                    normalized[field] = int(meta[field])

                                # string field for static map identifier.
                                normalized['map_id'] = str(meta['map_id'])

                                decoded_data['metadata'] = normalized
                            else:
                                # Any future auxiliary fields are passed through as UTF-8 strings.
                                value_str = value.decode('utf-8') if isinstance(value, bytes) else value
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
