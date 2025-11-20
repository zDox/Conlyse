"""
Converter for transforming recorder data to replay format.
"""
import json
import pickle
from datetime import datetime
from pathlib import Path
from typing import List, Literal, Optional, Tuple

import zstandard as zstd

from conflict_interface.data_types.game_object import parse_any
from conflict_interface.data_types.game_state.game_state import GameState
from conflict_interface.data_types.static_map_data import StaticMapData
from conflict_interface.logger_config import get_logger
from conflict_interface.replay.make_bireplay_patch import make_bireplay_patch
from conflict_interface.replay.replay import Replay
from conflict_interface.replay.replay_patch import BidirectionalReplayPatch
from conflict_interface.utils.helper import unix_ms_to_datetime

logger = get_logger()


class RecordToReplayConverter:
    """
    Converts recorder data to replay format.
    
    The recorder stores compressed game states and JSON responses in binary files.
    This converter reads those files and creates a replay database with bidirectional
    patches for efficient time travel.
    
    Supports two modes for creating patches:
    - 'state': Use make_bireplay_patch on consecutive game states (default)
    - 'json': Parse JSON responses and apply updates to create patches
    """
    
    def __init__(self, recording_dir: str, patch_mode: Literal['state', 'json'] = 'state'):
        """
        Initialize converter with recording directory.
        
        Args:
            recording_dir: Path to the recording directory containing game_states.bin
            patch_mode: Mode for creating patches - 'state' or 'json'
        """
        self.recording_dir = Path(recording_dir)
        self.game_states_file = self.recording_dir / "game_states.bin"
        self.responses_file = self.recording_dir / "responses.jsonl.zst"
        self.static_map_data_file = self.recording_dir / "static_map_data.bin"
        self.patch_mode = patch_mode
        
        if not self.recording_dir.exists():
            raise FileNotFoundError(f"Recording directory not found: {recording_dir}")
        if not self.game_states_file.exists():
            raise FileNotFoundError(f"Game states file not found: {self.game_states_file}")
        
        if patch_mode == 'json' and not self.responses_file.exists():
            raise FileNotFoundError(f"JSON responses file not found: {self.responses_file}. Required for 'json' mode.")
        
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
    
    def _read_json_responses(self) -> List[Tuple[int, dict]]:
        """
        Read all JSON responses from the recording.
        
        Returns:
            List of (timestamp_ms, json_response) tuples
        """
        json_responses = []
        
        with open(self.responses_file, 'rb') as f:
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
                
                # Decompress and parse JSON
                decompressed = self._decompressor.decompress(compressed_data)
                json_response = json.loads(decompressed.decode('utf-8'))
                
                json_responses.append((timestamp_ms, json_response))
        
        logger.info(f"Read {len(json_responses)} JSON responses from recording")
        return json_responses
    
    def _create_patch_from_json(self, prev_state: GameState, json_response: dict, game_interface) -> BidirectionalReplayPatch:
        """
        Create a bidirectional patch by parsing JSON response and applying it to previous state.
        
        Args:
            prev_state: Previous game state
            json_response: JSON response to apply
            game_interface: Game interface for parsing context
            
        Returns:
            BidirectionalReplayPatch
        """
        # Parse JSON response into GameState
        new_state = parse_any(GameState, json_response, game_interface)
        
        # Create bidirectional patch using the parsed states
        return make_bireplay_patch(prev_state, new_state)
    
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
            if self.patch_mode == 'state':
                return self._convert_using_states(output_file, game_id, player_id)
            elif self.patch_mode == 'json':
                return self._convert_using_json(output_file, game_id, player_id)
            else:
                logger.error(f"Invalid patch mode: {self.patch_mode}")
                return False
                
        except Exception as e:
            logger.error(f"Error converting recording: {e}", exc_info=True)
            return False
    
    def _convert_using_states(self, output_file: str, game_id: int = None, player_id: int = None) -> bool:
        """
        Convert using state-based approach (make_bireplay_patch on consecutive states).
        
        Args:
            output_file: Path to the output replay database file
            game_id: Game ID (extracted from first state if not provided)
            player_id: Player ID (extracted from first state if not provided)
            
        Returns:
            bool: True if successful, False otherwise
        """
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
        
        logger.info(f"Converting recording to replay using state-based mode: game_id={game_id}, player_id={player_id}")
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
    
    def _convert_using_json(self, output_file: str, game_id: int = None, player_id: int = None) -> bool:
        """
        Convert using JSON-based approach (parse JSON responses and apply updates).
        
        Args:
            output_file: Path to the output replay database file
            game_id: Game ID (extracted from first state if not provided)
            player_id: Player ID (extracted from first state if not provided)
            
        Returns:
            bool: True if successful, False otherwise
        """
        # Read initial game state (first one)
        game_states = self._read_game_states()
        if not game_states:
            logger.error("No game states found in recording")
            return False
        
        first_timestamp_ms, first_state = game_states[0]
        
        # Read JSON responses (skip first if it's a placeholder)
        json_responses = self._read_json_responses()
        if not json_responses:
            logger.error("No JSON responses found in recording")
            return False
        
        # Extract game_id and player_id
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
        
        logger.info(f"Converting recording to replay using JSON-based mode: game_id={game_id}, player_id={player_id}")
        logger.info(f"Total JSON responses: {len(json_responses)}")
        
        # Create a mock game interface for parsing context
        from conflict_interface.interface.game_interface import GameInterface
        mock_game = GameInterface()
        mock_game.game_state = first_state
        first_state.set_game(mock_game)
        
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
            
            # Process JSON responses and create patches
            prev_state = first_state
            response_idx = 0
            
            # Skip the first response if it's a placeholder (contains "note" field)
            if json_responses and "note" in json_responses[0][1]:
                response_idx = 1
                logger.info("Skipping placeholder response for initial state")
            
            for i in range(response_idx, len(json_responses)):
                timestamp_ms, json_response = json_responses[i]
                current_datetime = unix_ms_to_datetime(timestamp_ms)
                
                logger.info(f"Creating patch from JSON {i-response_idx+1}/{len(json_responses)-response_idx} at {current_datetime}")
                
                try:
                    # Parse JSON response into new state
                    new_state = parse_any(GameState, json_response, mock_game)
                    new_state.set_game(mock_game)
                    
                    # Create bidirectional patch
                    bipatch = make_bireplay_patch(prev_state, new_state)
                    
                    # Record the patch
                    replay.record_bipatch(
                        time_stamp=current_datetime,
                        game_id=game_id,
                        player_id=player_id,
                        replay_patch=bipatch
                    )
                    
                    prev_state = new_state
                    mock_game.game_state = new_state
                    
                except Exception as e:
                    logger.error(f"Error processing JSON response at {current_datetime}: {e}")
                    # Continue with next response
                    continue
        
        logger.info(f"Successfully converted recording to replay: {output_file}")
        return True
