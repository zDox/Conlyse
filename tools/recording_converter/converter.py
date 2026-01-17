"""
Converter for transforming recorder data to replay format.
"""
from pathlib import Path

from conflict_interface.logger_config import get_logger
from tools.recording_converter.enums import OperatingMode
from tools.recording_converter.from_game_state_using_make_bipatch_to_replay import FromGameStateUsingMakeBiPatchToReplay
from tools.recording_converter.from_json_responses_using_update_to_replay import FromJsonResponsesUsingUpdateToReplay
from tools.recording_converter.from_recording_to_json import FromRecordingToJson
from tools.recording_converter.recording_reader import RecordingReader

logger = get_logger()



class RecordingConverter:
    """
    Converts recorder data to specified output format.
    
    The recorder stores compressed game states and JSON responses in binary files.
    This converter reads those files and outputs them either as json or creates a Replay
    
    Supports three operating modes:
    - from_game_state_using_make_bipatch_to_replay:
        Converts the recording to a Replay using make_bireplay_patch between two consecutive game_states
    - from_json_responses_using_update_to_replay:
        Converts the recording to a Replay using the update function on a GameState
    - from_recording_to_json:
        Converts the recording to multiple json files
    """
    
    def __init__(self, recording_dir: str | Path, operating_mode: OperatingMode):
        """
        Initialize converter with recording directory.
        
        Args:
            recording_dir: Path to the recording directory
            operating_mode: One of the three operating modes
        """
        self.path = Path(recording_dir)
        self.reader = RecordingReader(self.path)
        self.op_mode = operating_mode

        self.check_op_mode_requirements()

    def check_op_mode_requirements(self):
        if not self.reader.recording_dir.exists():
            raise FileNotFoundError(f"Recording directory not found: {self.reader.recording_dir}")


        if self.op_mode == OperatingMode.gmr:
            if not self.reader.game_states_file.exists():
                raise FileNotFoundError(f"Game state file not found: {self.reader.game_states_file}, necessary in op mode gmr")
        elif self.op_mode == OperatingMode.rur:
            if not self.reader.responses_file.exists():
                raise FileNotFoundError(f"Requests file not found: {self.reader.responses_file}, necessary in op mode rur")
        # Op Mode rtj has no requirements as it simply tries to convert as much as it can

    def convert(self, output: Path, overwrite: bool, limit: int = None, game_id: int = None, player_id: int = None) -> bool:
        """
        Convert the recording to a replay file.
        
        Args:
            output: Path to the output replay database file or folder to dump the json to
            overwrite: Whether to overwrite existing output files
            limit: Maximum number of entries to process
            game_id: Game ID
            player_id: Player ID
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if self.op_mode in (OperatingMode.gmr, OperatingMode.rur) and Path(output).exists() and not overwrite:
                logger.error(f"Output file already exists: {output}")
                return False
            if self.op_mode == OperatingMode.gmr:
                gmr = FromGameStateUsingMakeBiPatchToReplay(self.reader)
                return gmr.convert(output_file=output,
                                   overwrite=overwrite,
                                   limit=limit,
                                   game_id=game_id,
                                   player_id=player_id)
            elif self.op_mode == OperatingMode.rur:
                rur = FromJsonResponsesUsingUpdateToReplay(self.reader)
                return rur.convert(output_file=output,
                                   overwrite=overwrite,
                                   limit=limit,
                                   game_id=game_id,
                                   player_id=player_id)
            elif self.op_mode == OperatingMode.rtj:
                rtj = FromRecordingToJson(self.reader)
                return rtj.convert(output_dir=output,
                                   overwrite=overwrite,
                                   limit=limit)
            else:
                logger.error(f"Invalid patch mode: {self.op_mode}")
                return False
                
        except Exception as e:
            logger.error(f"Error converting recording: {e}", exc_info=True)
            return False