"""
Replay Roundtrip Verification Tool

This debug tool validates replay conversion accuracy by comparing:
1. Game states reconstructed from replay patches
2. Game states parsed directly from JSON responses

It helps identify discrepancies in the replay recording/playback pipeline.
"""

import logging
import pprint
from copy import deepcopy
from pathlib import Path
from typing import List, Optional

from deepdiff import DeepDiff
from tqdm import tqdm

from conflict_interface.data_types.game_object_json import dump_any
from conflict_interface.data_types.game_object_json import parse_any
from conflict_interface.data_types.game_state.game_state import GameState
from conflict_interface.interface.game_interface import GameInterface
from conflict_interface.interface.replay_interface import ReplayInterface
from conflict_interface.logger_config import setup_library_logger
from conflict_interface.replay.constants import ADD_OPERATION, REMOVE_OPERATION, REPLACE_OPERATION
from conflict_interface.utils.helper import unix_ms_to_datetime
from paths import TEST_DATA
from tools.recording_converter.converter import RecordingConverter
from tools.recording_converter.enums import OperatingMode
from tools.recording_converter.recording_reader import RecordingReader

logger = logging.getLogger("rp_rdtp")


class ReplayRoundtrip:
    """
    Debug tool for verifying replay conversion fidelity.

    Compares game states reconstructed from replay patches against states
    parsed directly from JSON responses to detect conversion issues.
    """

    # Constants
    GAME_ACTIVATION_ACTION = "UltActivateGameAction"
    FULL_STATE_TYPE = "ultshared.UltGameState"

    def __init__(
            self,
            recording_file_path: Path,
            replay_file_path: Path,
            player_id: int = 85,
            limit: int = 100,
            compare_start_index: int = 0,
            preconverted: bool = False
    ):
        """
        Initialize the roundtrip verification tool.

        Args:
            recording_file_path: Path to the source recording directory
            replay_file_path: Path to the replay file
            player_id: Player ID for the recording
            limit: Maximum number of JSON responses to process
            compare_start_index: Index to start comparing states (skip initial states)
            preconverted: If True, skip conversion and use existing replay file
        """
        self.recording_file_path = recording_file_path
        self.replay_file_path = replay_file_path
        self.player_id = player_id
        self.limit = limit
        self.compare_start_index = compare_start_index

        # Timing trackers for error analysis
        self.current_time = None
        self.last_time = None

        if not preconverted:
            self._convert_recording_to_replay()

    def _convert_recording_to_replay(self) -> None:
        """Convert the recording to replay format using the converter."""
        logger.info(f"Converting recording to replay: {self.recording_file_path}")
        logger.info(f"Output file: {self.replay_file_path}")

        converter = RecordingConverter(
            self.recording_file_path,
            OperatingMode.rur
        )

        success = converter.convert(
            output=self.replay_file_path,
            overwrite=True,
            game_id=12345,
            player_id=self.player_id,
            limit=self.limit
        )

        if not success:
            raise RuntimeError("Failed to convert recording to replay")

        logger.info("Conversion completed successfully")

    def run(self) -> bool:
        """
        Run the roundtrip verification test.

        Compares states from replay playback against states from JSON responses
        to verify replay conversion accuracy.

        Returns:
            True if all states match, False if discrepancies found
        """
        logger.info("=" * 80)
        logger.info("Starting Replay Roundtrip Verification")
        logger.info("=" * 80)

        # Initialize reader and replay interface
        reader = RecordingReader(self.recording_file_path)
        replay_interface = self._initialize_replay_interface()

        # Load JSON responses
        json_responses = reader.read_json_responses(self.limit)
        logger.info(f"Loaded {len(json_responses)} JSON responses")

        # Find initial game state
        initial_idx = self._find_initial_game_state_index(json_responses)
        if initial_idx is None:
            logger.error("Could not find initial game state")
            return False

        # Initialize reference state from recorder
        recorder_state = self._initialize_recorder_state(
            json_responses, initial_idx, replay_interface
        )

        # Compare all subsequent states
        success = self._compare_all_states(
            json_responses, initial_idx, recorder_state, replay_interface
        )

        if success:
            logger.info("=" * 80)
            logger.info("✓ All states match! Replay conversion is accurate.")
            logger.info("=" * 80)

        return success

    def _initialize_replay_interface(self) -> ReplayInterface:
        """Initialize and validate the replay interface."""
        logger.info(f"Opening replay interface: {self.replay_file_path}")

        replay_interface = ReplayInterface(self.replay_file_path)
        replay_interface.open(mode='r')

        # Validate replay structure
        replay_interface._replay.storage.path_tree.validate_tree_structure()
        logger.info("Replay structure validated successfully")

        # Initialize timing
        self.current_time = replay_interface._replay.get_start_time()
        logger.info(f"Replay start time: {self.current_time}")

        return replay_interface

    def _find_initial_game_state_index(self, json_responses: List) -> Optional[int]:
        """
        Find the index of the initial game state.

        The initial state is the response immediately after the last
        UltActivateGameAction in the recording.

        Args:
            json_responses: List of (timestamp, response) tuples

        Returns:
            Index of initial game state, or None if not found
        """
        logger.info(f"Searching for {self.GAME_ACTIVATION_ACTION}...")
        initial_idx = -1

        for i, (_, json_response) in enumerate(json_responses):
            if json_response.get("action") == self.GAME_ACTIVATION_ACTION:
                initial_idx = i + 1

        if initial_idx == -1:
            logger.error(f"{self.GAME_ACTIVATION_ACTION} not found")
            return None

        logger.info(f"Initial game state found at index {initial_idx}")
        return initial_idx

    def _initialize_recorder_state(
            self,
            json_responses: List,
            initial_idx: int,
            replay_interface: ReplayInterface
    ) -> GameState:
        """
        Parse and initialize the reference state from the recorder.

        Args:
            json_responses: List of JSON responses
            initial_idx: Index of initial game state
            replay_interface: Replay interface for timing

        Returns:
            Initial game state from recorder
        """
        mock_game = GameInterface()
        _, json_response = json_responses[initial_idx]

        recorder_state: GameState = parse_any(
            GameState, json_response["result"], mock_game
        )

        # Update timing
        self.last_time = self.current_time
        self.current_time = unix_ms_to_datetime(int(recorder_state.time_stamp))

        logger.info(f"Initialized recorder state at {self.current_time}")
        return recorder_state

    def _compare_all_states(
            self,
            json_responses: List,
            initial_idx: int,
            recorder_state: GameState,
            replay_interface: ReplayInterface
    ) -> bool:
        """
        Compare all game states between recorder and replay.

        Args:
            json_responses: List of JSON responses
            initial_idx: Index to start from
            recorder_state: Current state from recorder (will be updated)
            replay_interface: Replay interface for state reconstruction

        Returns:
            True if all states match, False on first mismatch
        """
        mock_game = GameInterface()
        num_states = len(json_responses) - initial_idx

        logger.info(f"Comparing {num_states} game states...")
        logger.info(f"Starting comparison from index {self.compare_start_index}")

        for i in tqdm(
                range(initial_idx, len(json_responses)),
                desc="Comparing States",
                unit="state",
                unit_scale=True
        ):
            timestamp_ms, json_response = json_responses[i]

            # Check for unexpected game activation
            if json_response.get("action") == self.GAME_ACTIVATION_ACTION:
                logger.error(f"Unexpected {self.GAME_ACTIVATION_ACTION} at index {i}")
                return False

            # Update recorder state
            recorder_state = self._update_recorder_state(
                json_response, recorder_state, mock_game
            )

            # Skip comparison if before start index
            if i < self.compare_start_index:
                continue

            # Update replay state
            applied_patches = replay_interface.jump_to(self.current_time)
            if applied_patches is None:
                logger.error("You forgot to return patches in jump_to!")
            replay_state = replay_interface.game_state

            # Compare states
            if self._compare_game_states(replay_state, recorder_state):
                continue

            # States don't match - perform detailed error analysis
            self._analyze_state_mismatch(
                i, replay_state, recorder_state, applied_patches, replay_interface
            )
            return False

        return True

    def _update_recorder_state(
            self,
            json_response: dict,
            current_state: GameState,
            mock_game: GameInterface
    ) -> GameState:
        """
        Update recorder state based on JSON response.

        Handles both full state replacements and incremental updates.

        Args:
            json_response: JSON response containing state data
            current_state: Current recorder state
            mock_game: Mock game interface for parsing

        Returns:
            Updated game state
        """
        new_state: GameState = parse_any(
            GameState, json_response["result"], mock_game
        )

        # Update timing
        self.last_time = self.current_time
        self.current_time = unix_ms_to_datetime(int(new_state.time_stamp))

        # Handle full state replacement vs incremental update
        if json_response["result"]["@c"] == self.FULL_STATE_TYPE:
            return new_state
        else:
            current_state.update(new_state, [])
            return current_state

    def _compare_game_states(
            self,
            replay_state: GameState,
            recorder_state: GameState
    ) -> bool:
        """
        Compare two game states for equality.

        Args:
            replay_state: State reconstructed from replay patches
            recorder_state: State parsed from JSON responses

        Returns:
            True if states are identical, False otherwise
        """
        dict_replay = dump_any(replay_state)
        dict_recorder = dump_any(recorder_state)

        return dict_replay == dict_recorder

    def _analyze_state_mismatch(
            self,
            response_index: int,
            replay_state: GameState,
            recorder_state: GameState,
            applied_patches: List,
            replay_interface: ReplayInterface
    ) -> None:
        """
        Perform detailed analysis when states don't match.

        This method dumps debug information including:
        - Timing information
        - Deep diff of the states
        - Applied patches
        - Tree structure validation

        Args:
            response_index: Index of the response where mismatch occurred
            replay_state: State from replay
            recorder_state: State from recorder
            applied_patches: Patches applied to reach this state
            replay_interface: Replay interface for debugging
        """
        logger.error("")
        logger.error("=" * 80)
        logger.error("STATE MISMATCH DETECTED - Error Analysis")
        logger.error("=" * 80)
        logger.error(f"Response index: {response_index}")
        logger.error(f"Time range: {self.last_time} → {self.current_time}")
        logger.error("")

        # Capture state before and after for debugging
        replay_interface.jump_to(self.last_time)
        replay_state_before = deepcopy(replay_interface.game_state)
        replay_interface.jump_to(self.current_time)
        replay_state_after = replay_interface.game_state

        # Show detailed diff
        logger.error("Deep diff between replay and recorder states:")
        dict_replay = dump_any(replay_state)
        dict_recorder = dump_any(recorder_state)
        diff = DeepDiff(dict_replay, dict_recorder)
        pprint.pprint(diff)
        logger.error("")

        # Validate tree structure
        replay_interface._replay.storage.path_tree.validate_tree_structure()
        logger.error("Tree structure validation passed")
        logger.error("")

        # Analyze patches
        self._log_applied_patches(
            applied_patches,
            replay_interface._replay.storage.path_tree
        )

        logger.error("=" * 80)
        logger.error("Error Analysis Complete")
        logger.error("=" * 80)

    def _log_applied_patches(self, patches: List, path_tree) -> None:
        """
        Log details of applied patches for debugging.

        Args:
            patches: List of patches that were applied
            path_tree: Path tree for converting indices to paths
        """
        if not patches:
            logger.error("No patches were applied")
            return

        if len(patches) == 1:
            logger.error("1 patch applied:")
            self._log_single_patch(patches[0], path_tree)
        else:
            logger.error(f"{len(patches)} patches applied:")
            for idx, patch in enumerate(patches, 1):
                logger.error("")
                logger.error(f"Patch {idx}: {patch.from_timestamp} → {patch.to_timestamp}")
                self._log_single_patch(patch, path_tree)

    def _log_single_patch(self, patch, path_tree) -> None:
        """
        Log operations from a single patch.

        Args:
            patch: Single patch object
            path_tree: Path tree for converting indices to paths
        """
        num_ops = len(patch.op_types)
        logger.error(f"  {num_ops} operations:")

        for op_idx, (op_type, path_idx, value) in enumerate(
                zip(patch.op_types, patch.paths, patch.values)
        ):
            # Convert path index to human-readable path
            debug_path = path_tree.idx_to_path_list(path_idx)

            # Format operation based on type
            if op_type == ADD_OPERATION:
                value_str = str(value)[:100]
                logger.error(f"    [{op_idx}] ADD: {debug_path}")
                logger.error(f"         Value: {value_str}")
            elif op_type == REPLACE_OPERATION:
                value_str = str(value)[:100]
                logger.error(f"    [{op_idx}] REPLACE: {debug_path}")
                logger.error(f"         New value: {value_str}")
            elif op_type == REMOVE_OPERATION:
                logger.error(f"    [{op_idx}] REMOVE: {debug_path}")
            else:
                logger.error(f"    [{op_idx}] UNKNOWN OP ({op_type}): {debug_path}")


def main():
    """
    Main entry point for running the roundtrip verification test.

    Usage:
        python replay_roundtrip.py
    """
    # Configure logging
    setup_library_logger(logging.INFO)
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Run verification test
    roundtrip = ReplayRoundtrip(
        recording_file_path=TEST_DATA / "test008",
        replay_file_path=TEST_DATA / "test_replay_roundtrip.bin",
        player_id=85,
        limit=100,
        compare_start_index=0,
        preconverted=False
    )

    success = roundtrip.run()

    if not success:
        logger.error("Roundtrip verification failed!")
        exit(1)
    else:
        logger.info("Roundtrip verification passed!")
        exit(0)


if __name__ == "__main__":
    main()