from __future__ import annotations

from pathlib import Path
from typing import Callable
from typing import Optional
from typing import TYPE_CHECKING

from conflict_interface.game_object.game_object_parse_json import JsonParser
from conflict_interface.logger_config import get_logger
from conflict_interface.replay.make_bipatch_between_gamestates import make_bireplay_patch
from conflict_interface.replay.replay_patch import BidirectionalReplayPatch
from conflict_interface.replay.replay_timeline import ReplayTimeline
from conflict_interface.utils.helper import unix_ms_to_datetime

if TYPE_CHECKING:
    from conflict_interface.data_types.newest.game_state.game_state import GameState
    from conflict_interface.data_types.newest.static_map_data import StaticMapData

logger = get_logger()

class ReplayBuilder:
    """
    Usage:
    1. Import everything needed for all wanted version
    2. call .setup_parsers()
    3. everything else as normal
    """
    # Constants
    AUTO_STATE_TYPE = "ultshared.UltAutoGameState"
    FULL_STATE_TYPE = "ultshared.UltGameState"
    PATCH_BUFFER_MULTIPLIER = 2
    MAX_PATCHES = 10000
    built = False
    def __init__(self, path: Path, game_id: int, player_id: int):
        self.path = path

        self.parsers: dict[int, JsonParser] = {}
        self.replay_timeline: Optional[ReplayTimeline] = None
        self.game_id = game_id
        self.player_id = player_id

        self.created = path.exists()

    def setup_parsers(self):
        versions: list[int] = list(JsonParser.GAME_STATES.keys())
        for v in versions:
            self.parsers[v] = JsonParser(v)

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
            static_map_data: Optional[StaticMapData] = None) -> int:
        """
        Create a new replay from JSON responses.
        
        Args:
            json_responses: List of (timestamp, response) tuples
            static_map_data: Optional static map data for the replay (if None, static map will not be recorded)

        Returns:
            Index of the initial state that was used to create the replay
        """
        if self.created:
            raise ValueError("Replay already created.")

        initial_index = self._find_initial_game_state_index(json_responses)
        if initial_index == -1:
            raise ValueError("Initial game state not found.")

        # Parse initial game state
        _, initial_json = json_responses[initial_index]
        version = initial_json["client_version"]
        parser = self.parsers[version]
        initial_state: GameState = parser.parse_game_state(initial_json["result"], None)

        current_timestamp = unix_ms_to_datetime(int(initial_state.time_stamp))

        self.replay_timeline = ReplayTimeline(
            file_path=self.path,
            mode='a',
            game_id=self.game_id,
            player_id=self.player_id,
        )
        self.replay_timeline.open()

        logger.debug("Recording static map data to replay")

        if static_map_data is None:
            logger.debug("No static map data provided; skipping static map recording")
        logger.info(f"Recording initial game state at {current_timestamp} (game time)")
        self.replay_timeline.que_append_patch(version, to_time_stamp=current_timestamp,replay_patch=None, current_game_state=initial_state, static_map_data=static_map_data)

        # Clear game references and update replay's last state
        self.created = True
        
        # Return the initial index so the caller knows which responses were already processed
        return initial_index

    def append_json_responses(self,
                              json_responses: list[tuple[int, dict]],
                              progress_callback: Optional[Callable[[int, int], None]] = None):
        if not self.created:
            raise ValueError("Replay not created yet.")

        # --- SETUP TIMELINE ---
        if self.replay_timeline is None:
            self.replay_timeline = ReplayTimeline(self.path, mode="a", game_id=self.game_id, player_id=self.player_id)
            self.replay_timeline.open()

        self.replay_timeline.set_mode("a")
        self.replay_timeline.open()
        self.replay_timeline.execute_append_que()

        current_state = self.replay_timeline.get_last_game_state()

        if current_state is None:
            self.replay_timeline.close()
            raise ValueError("No last game state found in replay")

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
            version = json_response["client_version"]
            self.replay_timeline.latest_version = version
            parser = self.parsers[version]
            new_state: GameState = parser.parse_game_state(
                json_response["result"], None
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
            self.replay_timeline.que_append_patch(
                version = version,
                to_time_stamp=current_timestamp,
                replay_patch=bipatch,
                current_game_state=current_state
            )

        # Finalize
        logger.debug("Finalizing replay...")
        self.replay_timeline.execute_append_que()
        self.replay_timeline.set_last_game_state(current_state)
        self.replay_timeline.close()

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