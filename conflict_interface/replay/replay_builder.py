from pathlib import Path
from typing import Callable
from typing import Optional

from conflict_interface.data_types.game_object import GameObject
from conflict_interface.data_types.game_object_parse_json import JsonParser
from conflict_interface.data_types.game_state.game_state import GameState
from conflict_interface.data_types.static_map_data import StaticMapData
from conflict_interface.interface import GameInterface
from conflict_interface.logger_config import get_logger
from conflict_interface.replay.make_bipatch_between_gamestates import make_bireplay_patch
from conflict_interface.replay.replay import Replay
from conflict_interface.replay.replay_patch import BidirectionalReplayPatch
from conflict_interface.replay.replay_timeline import ReplayTimeline
from conflict_interface.utils.helper import unix_ms_to_datetime

logger = get_logger()

class ReplayBuilder:
    # Constants
    AUTO_STATE_TYPE = "ultshared.UltAutoGameState"
    FULL_STATE_TYPE = "ultshared.UltGameState"
    PATCH_BUFFER_MULTIPLIER = 2
    MAX_PATCHES = 10000

    def __init__(self, path: Path, game_id: int, player_id: int):
        self.path = path
        # Initialize parser
        self.parser = JsonParser()
        self.parser.type_graph.build_graph()
        self.parser.type_graph.add_c_tag(GameState, "ultshared.UltAutoGameState")

        self.replay: Optional[ReplayTimeline] = None
        self.game_id = game_id
        self.player_id = player_id

        self.created = path.exists()

    @staticmethod
    def _find_initial_game_state_index(json_responses: list[tuple[int, dict]]) -> int:
        """
        Find the index of the first game state after game activation.

        Args:
            json_responses: List of (timestamp, response) tuples

        Returns:
            Index of initial game state, or -1 if not found
        """
        logger.debug(f"Searching for {ReplayBuilder.FULL_STATE_TYPE} in responses...")

        for i, (_, json_response) in enumerate(json_responses):
            if "result" in json_response:
                if json_response["result"].get("@c") == ReplayBuilder.FULL_STATE_TYPE:
                    return i
        return -1

    def create_replay(
            self,
            json_responses: list[tuple[int, dict]],
            static_map_data: StaticMapData,
            max_patches: Optional[int] = None) -> int:
        """
        Create a new replay from JSON responses.
        
        Args:
            json_responses: List of (timestamp, response) tuples
            static_map_data: Static map data for the replay
            max_patches: Maximum number of patches to allocate
            
        Returns:
            Index of the initial state that was used to create the replay
        """
        if self.created:
            raise ValueError("Replay already created.")

        initial_index = self._find_initial_game_state_index(json_responses)
        if initial_index == -1:
            raise ValueError("Initial game state not found.")

        # Create mock game interface for parsing
        mock_game = GameInterface()

        # Parse initial game state
        _, initial_json = json_responses[initial_index]
        initial_state: GameState = self.parser.parse_any(
            GameState, initial_json["result"], mock_game
        )
        current_timestamp = unix_ms_to_datetime(int(initial_state.time_stamp))

        self.replay = ReplayTimeline(
            file_path=self.path,
            mode='w',
            game_id=self.game_id,
            player_id=self.player_id,
            max_patches=ReplayBuilder.MAX_PATCHES if max_patches is None else max_patches
        )
        self.replay.open()

        logger.debug("Recording static map data to replay")

        self.replay.record_static_map_data(
                static_map_data=static_map_data,
                game_id=self.game_id,
                player_id=self.player_id
        )
        logger.info(f"Recording initial game state at {current_timestamp} (game time)")
        self.replay.record_initial_game_state(
            time_stamp=current_timestamp,
            game_id=self.game_id,
            player_id=self.player_id,
            game_state=initial_state
        )

        # Clear game references and update replay's last state
        GameObject.set_game_recursive(initial_state, None)
        self.replay.set_last_game_state(initial_state)
        self.replay.close()
        self.created = True
        
        # Return the initial index so the caller knows which responses were already processed
        return initial_index

    def append_json_responses(self,
                              json_responses: list[tuple[int, dict]],
                              progress_callback: Optional[Callable[[int, int], None]] = None):
        if not self.created:
            raise ValueError("Replay not created yet.")

        if self.replay is None:
            self.replay = Replay(self.path, mode="a", game_id=self.game_id, player_id=self.player_id)
            self.replay.open()
        elif self.replay.is_open() and self.replay.mode != 'a':
            self.replay.close()
            self.replay = Replay(self.path, mode="a", game_id=self.game_id, player_id=self.player_id)
            self.replay.open()
        elif not self.replay.is_open():
            self.replay = Replay(self.path, mode="a", game_id=self.game_id, player_id=self.player_id)
            self.replay.open()

        current_state = self.replay.storage.last_game_state

        if current_state is None:
            self.replay.close()
            raise ValueError("No last game state found in replay")

        # Create mock game interface for parsing
        mock_game = GameInterface()

        # Process JSON responses
        num_responses = len(json_responses)
        logger.debug(f"Appending {num_responses} state updates...")

        for i in range(len(json_responses)):
            if progress_callback:
                progress_callback(i, num_responses)

            _, json_response = json_responses[i]

            # Skip everything except game state updates
            if not ("result" in json_response) or json_response["result"].get("@c") not in (ReplayBuilder.FULL_STATE_TYPE, ReplayBuilder.AUTO_STATE_TYPE):
                continue

            # Parse new state
            new_state: GameState = self.parser.parse_any(
                GameState, json_response["result"], mock_game
            )
            current_timestamp = unix_ms_to_datetime(int(new_state.time_stamp))

            # Create appropriate patch
            bipatch = ReplayBuilder._create_patch_from_json(
                json_response, current_state, new_state
            )

            # Update current state if full replacement
            if json_response["result"]["@c"] == ReplayBuilder.FULL_STATE_TYPE:
                current_state = new_state

            # Record patch to replay
            self.replay.que_append_patch(
                time_stamp=current_timestamp,
                game_id=self.game_id,
                player_id=self.player_id,
                replay_patch=bipatch,
            )

        # Finalize
        logger.debug("Finalizing replay...")
        self.replay.execute_append_que()
        GameObject.set_game_recursive(current_state, None)
        self.replay.set_last_game_state(current_state)
        self.replay.close()

        logger.debug(f"Successfully appended to replay: {self.path}")
        return True

    @staticmethod
    def _create_patch_from_json(
            json_response: dict,
            current_state: GameState,
            new_state: GameState
    ) -> BidirectionalReplayPatch:
        """
        Create a bidirectional patch based on response type.

        Full state replacements use make_bireplay_patch for complete comparison.
        Incremental updates use GameState.update() to track specific changes.
        """
        if json_response["result"]["@c"] == ReplayBuilder.FULL_STATE_TYPE:
            # Full state replacement - compare entire states
            return make_bireplay_patch(current_state, new_state)
        else:
            # Incremental update - track specific changes
            bipatch = BidirectionalReplayPatch()
            current_state.update(new_state, path=[], rp=bipatch)
            return bipatch