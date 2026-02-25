"""
Storage manager for handling hot and cold storage of replay files.
"""
from pathlib import Path
from typing import Optional
import boto3
import logging

logger = logging.getLogger(__name__)

class ColdStorageManager:
    """Manages replay files in cold (S3) storage."""
    
    def __init__(self, s3_config):
        """
        Initialize cold storage manager.
        
        Args:
            s3_config: S3Config instance with connection details
        """
        self.s3_config = s3_config
        self.s3_client = boto3.client(
            's3',
            endpoint_url=s3_config.endpoint_url,
            aws_access_key_id=s3_config.access_key,
            aws_secret_access_key=s3_config.secret_key,
            region_name=s3_config.region
        )
        self.bucket_name = s3_config.bucket_name
        
        # Ensure bucket exists
        self._ensure_bucket()
        
    def _ensure_bucket(self):
        """Ensure the S3 bucket exists."""
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
        except Exception as e:
            logger.info(f"Creating S3 bucket: {self.bucket_name}")
            try:
                self.s3_client.create_bucket(Bucket=self.bucket_name)
            except Exception as create_error:
                logger.error(f"Failed to create bucket: {create_error}")
                
    def upload_replay(self, local_path: Path, game_id: int, player_id: int) -> Optional[str]:
        """
        Upload a replay file to cold storage.
        
        Args:
            local_path: Path to the local replay file
            game_id: Game ID
            player_id: Player ID
            
        Returns:
            S3 key/path if successful, None otherwise
        """
        if not local_path.exists():
            logger.error(f"Local file not found: {local_path}")
            return None
            
        s3_key = f"replays/game_{game_id}_player_{player_id}.bin"
        
        try:
            self.s3_client.upload_file(
                str(local_path),
                self.bucket_name,
                s3_key
            )
            logger.info(f"Uploaded replay to S3: {s3_key}")
            return f"s3://{self.bucket_name}/{s3_key}"
        except Exception as e:
            logger.error(f"Failed to upload to S3: {e}")
            return None
            
    def download_replay(self, s3_key: str, local_path: Path) -> bool:
        """
        Download a replay file from cold storage.
        
        Args:
            s3_key: S3 object key
            local_path: Where to save the file locally
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.s3_client.download_file(
                self.bucket_name,
                s3_key,
                str(local_path)
            )
            logger.info(f"Downloaded replay from S3: {s3_key}")
            return True
        except Exception as e:
            logger.error(f"Failed to download from S3: {e}")
            return False
            
    def replay_exists(self, game_id: int, player_id: int) -> bool:
        """
        Check if a replay exists in cold storage.
        
        Args:
            game_id: Game ID
            player_id: Player ID
            
        Returns:
            True if replay exists in S3
        """
        s3_key = f"replays/game_{game_id}_player_{player_id}.db"
        
        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=s3_key)
            return True
        except Exception as e:
            # Log the error but don't fail
            logger.debug(f"Replay not found in S3: {e}")
            return False
