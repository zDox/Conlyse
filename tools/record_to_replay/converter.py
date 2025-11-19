"""
Converter for transforming recorder data to replay format.
"""
import pickle
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

import zstandard as zstd

from conflict_interface.data_types.game_state.game_state import GameState
from conflict_interface.data_types.static_map_data import StaticMapData
from conflict_interface.logger_config import get_logger
from conflict_interface.replay.make_bireplay_patch import make_bireplay_patch
from conflict_interface.replay.replay import Replay
from conflict_interface.utils.helper import unix_ms_to_datetime

logger = get_logger()


class RecordToReplayConverter:
    """
    Converts recorder data to replay format.
    
    The recorder stores compressed game states and JSON responses in binary files.
    This converter reads those files and creates a replay database with bidirectional
    patches for efficient time travel.
    """
    
    def __init__(self, recording_dir: str):
        """
        Initialize converter with recording directory.
        
        Args:
            recording_dir: Path to the recording directory containing game_states.bin
        """
        self.recording_dir = Path(recording_dir)
        self.game_states_file = self.recording_dir / "game_states.bin"
        self.static_map_data_file = self.recording_dir / "static_map_data.bin"
        
        if not self.recording_dir.exists():
            raise FileNotFoundError(f"Recording directory not found: {recording_dir}")
        if not self.game_states_file.exists():
            raise FileNotFoundError(f"Game states file not found: {self.game_states_file}")
        
        self._decompressor = zstd.ZstdDecompressor()
    
    def _read_static_map_data(self) -> Optional[StaticMapData]:
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
    
    def _read_game_states(self) -> List[Tuple[int, GameState]]:
        """
        Read all game states from the recording.
        
        Returns:
            List of (timestamp_ms, game_state) tuples
        """
        game_states = []
        
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
                    break
                
                length = int.from_bytes(length_bytes, 'big')
                
                # Read compressed data
                compressed_data = f.read(length)
                if len(compressed_data) != length:
                    logger.warning(f"Incomplete data at timestamp {timestamp_ms}")
                    break
                
                # Decompress and unpickle
                decompressed = self._decompressor.decompress(compressed_data)
                game_state = pickle.loads(decompressed)
                
                game_states.append((timestamp_ms, game_state))
        
        logger.info(f"Read {len(game_states)} game states from recording")
        return game_states
    
    def convert(self, output_file: str, game_id: int = None, player_id: int = None) -> bool:
        """
        Convert the recording to a replay file.
        
        Args:
            output_file: Path to the output replay database file
            game_id: Game ID (extracted from first state if not provided)
            player_id: Player ID (extracted from first state if not provided)
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Read all game states
            game_states = self._read_game_states()
            
            if not game_states:
                logger.error("No game states found in recording")
                return False
            
            # Extract game_id and player_id from first state if not provided
            first_timestamp_ms, first_state = game_states[0]
            
            if game_id is None:
                if hasattr(first_state, 'game_id'):
                    game_id = first_state.game_id
                else:
                    logger.error("Could not determine game_id from recording")
                    return False
            
            if player_id is None:
                if hasattr(first_state, 'player_id'):
                    player_id = first_state.player_id
                elif hasattr(first_state.states, 'player_state') and hasattr(first_state.states.player_state, 'player_id'):
                    player_id = first_state.states.player_state.player_id
                else:
                    logger.warning("Could not determine player_id from recording, using 0")
                    player_id = 0
            
            logger.info(f"Converting recording to replay: game_id={game_id}, player_id={player_id}")
            logger.info(f"Total game states: {len(game_states)}")
            
            # Create replay in write mode
            with Replay(filename=output_file, mode='w', game_id=game_id, player_id=player_id) as replay:
                # Record initial game state
                first_datetime = unix_ms_to_datetime(first_timestamp_ms)
                logger.info(f"Recording initial state at {first_datetime}")
                replay.record_initial_game_state(
                    time_stamp=first_datetime,
                    game_id=game_id,
                    player_id=player_id,
                    game_state=first_state
                )
                
                # Record static map data if available
                static_map_data = self._read_static_map_data()
                if static_map_data:
                    logger.info("Recording static map data")
                    replay.record_static_map_data(
                        static_map_data=static_map_data,
                        game_id=game_id,
                        player_id=player_id
                    )
                elif hasattr(first_state, 'static_map_data') and first_state.static_map_data:
                    logger.info("Recording static map data from first state")
                    replay.record_static_map_data(
                        static_map_data=first_state.static_map_data,
                        game_id=game_id,
                        player_id=player_id
                    )
                
                # Create patches between consecutive states
                prev_state = first_state
                for i in range(1, len(game_states)):
                    timestamp_ms, current_state = game_states[i]
                    current_datetime = unix_ms_to_datetime(timestamp_ms)
                    
                    logger.info(f"Creating patch {i}/{len(game_states)-1} at {current_datetime}")
                    
                    # Create bidirectional patch
                    bipatch = make_bireplay_patch(prev_state, current_state)
                    
                    # Record the patch
                    replay.record_bipatch(
                        time_stamp=current_datetime,
                        game_id=game_id,
                        player_id=player_id,
                        replay_patch=bipatch
                    )
                    
                    prev_state = current_state
            
            logger.info(f"Successfully converted recording to replay: {output_file}")
            return True
            
        except Exception as e:
            logger.error(f"Error converting recording: {e}", exc_info=True)
            return False
