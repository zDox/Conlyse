from __future__ import annotations

import bisect
import gc

from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import Callable
from typing import Literal
from typing import TYPE_CHECKING
from typing import override

from conflict_interface.hook_system.replay_hook import ReplayHook
from conflict_interface.hook_system.replay_hook_event import ReplayHookEvent
from conflict_interface.hook_system.replay_hook_system import ReplayHookSystem
from conflict_interface.hook_system.replay_hook_tag import ReplayHookTag
from conflict_interface.interface.game_interface import GameInterface
from conflict_interface.logger_config import get_logger
from conflict_interface.replay.constants import ADD_OPERATION
from conflict_interface.replay.constants import REMOVE_OPERATION
from conflict_interface.replay.constants import REPLACE_OPERATION
from conflict_interface.replay.long_patch import create_long_patch
from conflict_interface.replay.patch_graph import PatchGraph
from conflict_interface.replay.patch_graph_node import PatchGraphNode
from conflict_interface.replay.replay_timeline import ReplayTimeline
from conflict_interface.replay.replay_segment import ReplaySegment

if TYPE_CHECKING:
    from conflict_interface.data_types.newest.map_state.province import Province

logger = get_logger()

LONG_PATCH_THRESHOLD = 10

class ReplayInterface(GameInterface):
    def __init__(self, file_path: Path | str, static_map_data: dict[str, Path] | None = None, player_id: int | None = None, game_id: int | None = None):
        """
        Initialize a replay-only game interface backed by a recorded replay file.

        This does not open or parse the replay immediately. Call ``open()`` before
        accessing timestamps or game state.

        Args:
            file_path: Path to the replay file produced by the recording/online interface.
            static_map_data: Mapping from game version to the path of the corresponding
                static map data file. The files are eagerly read and cached.
            player_id: Optional player identifier to associate with this replay. If not
                provided, it may be inferred from the replay metadata when opening.
            game_id: Optional game identifier for the replay; used for metadata and
                hook system initialization.
        """
        super().__init__()
        self.current_time: datetime | None = None
        self.current_timestamp_index: int = 0
        self.player_id: int | None = player_id
        self.game_id: int | None = game_id

        self._file_path: Path = Path(file_path)
        self._replay: ReplayTimeline | None = None
        self._hook_system: ReplayHookSystem | None = None
        self._current_segment: ReplaySegment | None = None

        # Mapping from map_id -> path to static map data.
        self._static_map_paths: dict[str, Path] = {k: Path(v) for k, v in (static_map_data or {}).items()}
        # Cache from map_id -> loaded StaticMapData object.
        self._static_map_cache: dict[str, object] = {}

        self._is_open: bool = False



    def open(self, mode: Literal['r', 'read metadata'] = 'r') -> bool:
        if self._is_open:
            logger.warning("Replay is already open. Closing it for you ;)")
            self.close()

        logger.debug("Opening Replay")

        if mode not in ("r", "read metadata"):
            raise ValueError(f"Unsupported replay open mode: {mode}")


        self._replay = ReplayTimeline(self._file_path, mode, player_id=self.player_id, game_id=self.game_id)
        self._replay.open()

        # In full read mode, ensure that all required static map data is available.
        if mode == "r":
            self._validate_static_map_data()

        if mode == "read metadata":
            # Metadata-only mode: don't create hook system or load game state.
            self._is_open = True
            logger.debug("Metadata-only replay open completed successfully")
            return True

        # Full replay mode
        self._replay.set_game(self)
        self._hook_system = ReplayHookSystem(self._replay)

        # Attach static map data per segment based on map_id stored in metadata.
        for _, segment in self._replay.segments.items():
            # Link game objects back to this interface.
            segment.storage.initial_game_state.set_game(self)

            if not self._static_map_paths:
                continue

            meta = segment.storage.metadata
            map_id = getattr(meta, "map_id", "") if meta is not None else ""
            if not map_id:
                logger.warning("Segment has no map_id in metadata; static map data cannot be attached.")
                continue

            path = self._static_map_paths.get(map_id)
            if path is None:
                logger.warning(f"No static map path configured for map_id '{map_id}'.")
                continue

            if map_id not in self._static_map_cache:
                static_map = ReplayTimeline.read_static_map_data(segment.version, path)
                self._static_map_cache[map_id] = static_map
            else:
                static_map = self._static_map_cache[map_id]

            segment.storage.initial_game_state.states.map_state.map.set_static_map_data(static_map)

        first_segment = self._replay.find_first_segment()
        self._current_segment = first_segment
        self.game_state = first_segment.storage.initial_game_state

        # Step 5: final metadata
        self._update_player_id()
        self.current_time = first_segment.get_start_time()

        self._is_open = True
        logger.debug("Initialization Completed Successfully")
        return True

    def close(self):
        if not self._is_open:
            logger.warning("Tried to close replay that was not open!")
            return

        assert self._replay is not None, "Replay is None"

        self._replay.close()
        self._is_open = False

    def _update_player_id(self):
        valid_states = {"ACTIVE", "UNKNOWN", "INACTIVE", "ABANDONED"}

        # If current player_id exists and is valid, nothing to do
        if self.player_id is not None:
            player = self.get_player(self.player_id)
            if player.activity_state in valid_states:
                return

        # Otherwise, find any player with a valid state
        for player in self.get_players().values():
            if player.activity_state in valid_states:
                self.player_id = player.player_id
                self._replay.player_id = self.player_id
                return

        # No valid player found
        raise Exception("Could not determine player ID")

    def _validate_static_map_data(self) -> None:
        """
        Ensure that for all segments in this replay, any declared map_id has
        corresponding static map data configured and available on disk.

        Raises:
            ValueError: If static map data is missing or incomplete for any map_id.
        """
        if self._replay is None:
            return

        required_map_ids = self.get_required_map_ids()
        if not required_map_ids:
            raise ValueError(
                "Replay requires static map data for map_ids, "
                "but no map_ids were found in the replay metadata."
            )

        if not self._static_map_paths:
            raise ValueError(
                f"Replay requires static map data for map_ids {sorted(required_map_ids)}, "
                "but no static_map_data was provided to ReplayInterface."
            )

        missing_ids: list[str] = []
        missing_files: list[str] = []

        for map_id in required_map_ids:
            path = self._static_map_paths.get(map_id)
            if path is None:
                missing_ids.append(map_id)
            elif not path.is_file():
                missing_files.append(str(path))

        if missing_ids or missing_files:
            parts: list[str] = []
            if missing_ids:
                parts.append(f"missing map_ids: {sorted(missing_ids)}")
            if missing_files:
                parts.append(f"non-existent files: {missing_files}")

            message = "Static map data is incomplete for this replay: " + "; ".join(parts)
            logger.error(message)
            raise ValueError(message)

    @override
    def client_time(self) -> datetime:
        return self.current_time

    @property
    def start_time(self) -> datetime:
        return self._replay.get_start_time()

    @property
    def last_time(self) -> datetime:
        return self._replay.get_last_time()

    def get_segments_metadata(self):
        """
        Return per-segment metadata when the replay is opened (in any mode).
        """
        assert self._replay is not None, "Replay is not open"
        return self._replay.get_segments_metadata()

    def get_required_map_ids(self) -> set[str]:
        """
        Return the set of all map_ids referenced by segments in this replay.
        """
        metas = self.get_segments_metadata()
        return {m.map_id for m in metas.values() if getattr(m, "map_id", "")}

    def get_required_versions(self) -> set[int]:
        """
        Return the set of all datatype versions used by segments in this replay.
        """
        assert self._replay is not None, "Replay is not open"
        return {segment.version for segment in self._replay.segments.values()}

    def get_total_patches(self) -> int:
        """
        Return the total number of patches across all segments in this replay.
        """
        metas = self.get_segments_metadata()
        return sum(m.current_patches for m in metas.values())

    def jump_to(self, time_stamp: datetime, create_long_patches = True) -> None:
        """
        Jumps to the specified timestamp in the replay.

        Returns applied patches
        """

        if self.current_time == time_stamp:
            return

        if time_stamp < self._replay.get_start_time():
            self.game_state = self._replay.find_first_segment().initial_game_state
            return
        correct_segment = self._replay.find_segment(time_stamp)
        if not correct_segment:
            logger.warning(f"That time {time_stamp} is in no Segment, unable to jump!")
            return

        if correct_segment.get_last_time() != self._current_segment.get_last_time(): # TODO bettter comparison should be some sort of !=
            self.game_state = correct_segment.storage.initial_game_state
            self._hook_system.add_segment_switch_event()
            self._current_segment = correct_segment
            patches = self._current_segment.storage.patch_graph.find_patch_path(self._current_segment.get_start_time(),
                                                                                time_stamp)
        else:
            patches = self._current_segment.storage.patch_graph.find_patch_path(self.current_time,
                                                                                time_stamp)
        gc.disable()
        if PatchGraph.cost(patches) > LONG_PATCH_THRESHOLD and len(patches) > 1 and create_long_patches:
            patches = [self.create_and_save_long_patch(self.current_time, time_stamp)]

        self._apply_patches_and_update_state(patches, time_stamp)

        # Update the current timestamp index for O(1) next/previous operations
        self.current_timestamp_index = bisect.bisect_left(self._replay.get_timestamp_cache(), time_stamp)
        gc.collect(0)
        gc.enable()
        # DEBUG ----------------
        #return patches
        # ----------------------

    def _apply_patches_and_update_state(self, patches, target_time: datetime) -> None:
        """
        Helper method to apply patches and update game state.
        Reduces code duplication across jump methods.
        """
        for patch in patches:
            self._current_segment.apply_patch(patch, self.game_state, self)

        self.current_time = target_time
        #self._update_player_id()

        if hasattr(self, '_hook_system'):
            self._hook_system.execute_queue()

    def jump_to_next_patch(self) -> bool:
        """
        Jumps to the next patch in the replay.
        Optimized for O(1) sequential forward traversal.

        Returns:
            True if successfully jumped to next patch, False if at end of replay.
        """
        next_timestamp = self.get_next_timestamp()
        if next_timestamp is None:
            return False

        correct_segment = self._replay.find_segment(next_timestamp)
        if correct_segment != self._current_segment:
            self.jump_to(next_timestamp, False)
            return True

        patches = [self._current_segment.storage.patch_graph.patches[(int(self.current_time.timestamp()), int(next_timestamp.timestamp()))]]
        if patches:
            self._apply_patches_and_update_state(patches, next_timestamp)
            self.current_timestamp_index += 1

        return True

    def jump_to_previous_patch(self) -> bool:
        """
        Jumps to the previous patch in the replay.
        Requires reloading from initial state and applying patches up to target.

        Returns:
            True if successfully jumped to previous patch, False if at start of replay.
        """
        prev_ts = self.get_previous_timestamp()

        if prev_ts is None:
            return False

        correct_segment = self._replay.find_segment(prev_ts)
        if correct_segment != self._current_segment:
            self.jump_to(prev_ts, False)
            return True

        patches = [self._current_segment.storage.patch_graph.patches[(int(self.current_time.timestamp()), int(prev_ts.timestamp()))]]

        if patches:
            self._apply_patches_and_update_state(patches, prev_ts)
            self.current_timestamp_index -= 1

        return True

    def jump_to_last_time(self):
        self.jump_to(self._replay.get_last_time())

    def create_and_save_long_patch(self, from_time: datetime, to_time: datetime) -> PatchGraphNode:
        path_tree = self._current_segment.storage.path_tree
        patch_graph = self._current_segment.storage.patch_graph
        from_time_exact = self.find_closest_prev_timestamp(from_time)
        to_time_exact = self.find_closest_prev_timestamp(to_time)
        if from_time_exact is None or to_time_exact is None:
            raise ValueError(f"There are no timestamps satisfying this jump from {str(from_time)} to {str(to_time)}")
        long_patch_node = create_long_patch(from_time_exact, to_time_exact, patch_graph, path_tree)
        self._current_segment.storage.patch_graph.add_edge(long_patch_node)
        return long_patch_node

    def get_timestamps(self) -> list[datetime]:
        """
        Get all timestamps in the replay as datetime objects.

        Returns:
            Cached list of datetime timestamps (O(1) operation)
        """
        return self._replay.get_timestamp_cache()

    def get_next_timestamp(self, timestamp = None) -> datetime | None:
        """
        Gets the next timestamp after the given timestamp.
        O(1) when timestamp is None, O(log n) when a specific timestamp is provided.
        """
        ts = self._replay.get_timestamp_cache()

        if timestamp is None:
            # Use cached index for O(1) lookup
            next_idx = self.current_timestamp_index + 1
            return ts[next_idx] if next_idx < len(ts) else None

        # Fallback for custom timestamp (O(log n))
        i = bisect.bisect_right(ts, timestamp)
        return ts[i] if i < len(ts) else None

    def find_closest_prev_timestamp(self, target: datetime):
        """
        Find the closest cached timestamp less than or equal to the target.

        Parameters
        ----------
        target : datetime
            Target datetime (UTC).

        Returns
        -------
        datetime | None
            The closest datetime in ``self._time_stamps_cache`` that is
            less than or equal to ``target``, or ``None`` if no such timestamp
            exists.
        """
        # Convert datetime to Unix timestamp and delegate to PatchGraph
        target_unix = int(target.timestamp())
        prev_unix = self._current_segment.storage.patch_graph.find_prev_timestamp(target_unix)
        
        if prev_unix is None:
            return None
        
        # Convert back to datetime
        return datetime.fromtimestamp(prev_unix, tz=UTC)

    def get_previous_timestamp(self, timestamp = None) -> datetime | None:
        """
        Gets the previous timestamp before the given timestamp.
        O(1) when timestamp is None, O(log n) when a specific timestamp is provided.
        """
        ts = self._replay.get_timestamp_cache()

        if timestamp is None:
            # Use cached index for O(1) lookup
            prev_idx = self.current_timestamp_index - 1
            return ts[prev_idx] if prev_idx >= 0 else None

        # Fallback for custom timestamp (O(log n))
        i = bisect.bisect_left(ts, timestamp)
        return ts[i - 1] if i > 0 else None

    """
    Hook System
    """
    def get_hook_system(self) -> ReplayHookSystem:
        return self._hook_system

    def poll_events(self) -> dict[ReplayHookTag, list[ReplayHookEvent]]:
        events = self._hook_system.poll_events()
        grouped_events = {}
        for event in events:
            if event.tag not in grouped_events:
                grouped_events[event.tag] = []
            grouped_events[event.tag].append(event)
        return grouped_events

    def unregister_all_hooks(self):
        self._hook_system.unregister_all_hooks()

    def register_province_trigger(self, attributes: list[str]):
        path = ["states", "map_state", "map", "locations"]
        self._hook_system.register_event_trigger(
            tag=ReplayHookTag.ProvinceChanged,
            path=path,
            attributes=attributes
        )
    def unregister_province_trigger(self):
        path = ["states", "map_state", "map", "locations"]
        self._hook_system.unregister_event_trigger(path)

    def on_province_attribute_change(self, callback: Callable[[Province, dict], None], attributes: list[str]) -> None:
        """
        Register a callback for when an attribute of a province changes.

        The callback will be called with the province object:
        callback(province, changed_attributes)
        where province is the Province object of which at least one of
        the specified attributes has changed, and changed_attributes is a dict
        mapping attribute names to a tuple of (old_value, new_value).

        Args:
            callback: Function to call when the province attribute changes
            attributes: The name of the attributes to watch (e.g., ["owner_id", "resource_production"]).
        """
        path = ["states", "map_state", "map", "locations"]
        path_idx = self._current_segment.storage.path_tree.path_list_to_idx(path)

        hook = ReplayHook(
            tag=ReplayHookTag.ProvinceChanged,
            callback=callback,
            change_types=[ADD_OPERATION, REPLACE_OPERATION, REMOVE_OPERATION],
            attributes=attributes,
            path=path_idx
        )
        self._hook_system.register_hook(hook)

    def remove_province_attribute_change_callback(self, callback: Callable[[Province, dict], None]) -> None:
        """Remove a previously registered province attribute change hook."""

        path = ["states", "map_state", "map", "locations"]
        path_idx = self._current_segment.storage.path_tree.path_list_to_idx(path)
        self._hook_system.unregister_hook(path_idx, callback)

    def register_player_trigger(self, attributes: list[str] | None = None):
        path = ["states", "player_state", "players"]
        self._hook_system.register_event_trigger(
            tag=ReplayHookTag.PlayerChanged,
            path=path,
            attributes=attributes
        )
    def unregister_player_trigger(self):
        path = ["states", "player_state", "players"]
        self._hook_system.unregister_event_trigger(path)

    def register_team_trigger(self, attributes: list[str] | None = None):
        path = ["states", "player_state", "teams"]
        self._hook_system.register_event_trigger(
            tag=ReplayHookTag.TeamChanged,
            path=path,
            attributes=attributes
        )

    def unregister_team_trigger(self):
        path = ["states", "player_state", "teams"]
        self._hook_system.unregister_event_trigger(path)

    def register_army_trigger(self, attributes: list[str] | None = None):
        path = ["states", "army_state", "armies"]
        self._hook_system.register_event_trigger(
            tag=ReplayHookTag.ArmyChanged,
            path=path,
            attributes=attributes
        )

    def unregister_army_trigger(self):
        path = ["states", "army_state", "armies"]
        self._hook_system.unregister_event_trigger(path)

    def register_game_info_trigger(self, attributes: list[str] | None = None):
        path = ["states", "game_info_state"]
        self._hook_system.register_event_trigger(
            tag=ReplayHookTag.GameInfoChanged,
            path=path,
            attributes=attributes
        )

    def unregister_game_info_trigger(self):
        path = ["states", "game_info_state"]
        self._hook_system.unregister_event_trigger(path)