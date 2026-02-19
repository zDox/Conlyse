from datetime import datetime
from typing import Literal

from conflict_interface.logger_config import get_logger
from conflict_interface.replay.replay_patch import BidirectionalReplayPatch
from conflict_interface.replay.replaysegment import ReplaySegment

DEFAULT_MAX_PATCHES = 3000

logger = get_logger()

class ReplayTimeline:
    def __init__(self, mode: Literal['r', 'a'] = 'r'):
        self._mode: Literal['r','a'] = mode
        self._open = False
        self.segments: dict[tuple[datetime, datetime | None, int], ReplaySegment] = {} # [From_ts, To_ts, version] -> segment

        self.last_time: datetime | None = None

    def open(self):
        if self._open:
            return

        if self._mode == "a":
            for segment in self.segments.values():
                segment.load_append_mode()
        elif self._mode == "r":
            for segment in self.segments.values():
                segment.load_everything()
        pass

    def close(self):
        if not self._open:
            return
        if self._mode == "a":
            for segment in self.segments.values():
                segment.collapse_append_mode()
        pass

    def get_mode(self):
        return self._mode

    def set_mode(self, mode: Literal['r', 'a']):
        if mode == self._mode:
            return
        if self._open:
            self.close()
            self._mode = mode
            self.open()
        else:
            self._mode = mode

    def que_append_patch(self, version :int, to_time_stamp: datetime, game_id: int, player_id: int, replay_patch: BidirectionalReplayPatch):
        assert self._mode == "a"
        segment = self._find_open_segment(version)[1]
        if segment is None:
            segment = self._create_segment(version, self.last_time, game_id, player_id)

        if segment is None:
            raise Exception(f"Unable to create last segment in version: {version}")
        try:
            segment.que_append_patch(to_time_stamp, game_id, player_id, replay_patch)
        except IndexError:
            logger.warning(f"Had to increase max_patches for last segment in version: {version}")
            self._extend_segment(segment)
            segment.que_append_patch(to_time_stamp, game_id, player_id, replay_patch)
        self.last_time = to_time_stamp

    def execute_append_que(self):
        assert self._mode == "a"
        for segment in self.segments.values():
            segment.execute_append_que()

    def _find_open_segment(self, version: int) -> tuple | None:
        """Return the (key, segment) pair for the open segment of the given version, or None."""
        return next(
            ((key, seg) for (key, seg) in self.segments.items() if key[2] == version and key[1] is None),
            None
        )

    def _close_segment(self, key: tuple, close_timestamp: datetime) -> None:
        """Close an open segment by replacing its key with a bounded one."""
        from_ts, _, version = key
        segment = self.segments.pop(key)
        self.segments[(from_ts, close_timestamp, version)] = segment

    def _create_segment(self, version: int, from_timestamp: datetime, game_id: int, player_id: int) -> "ReplaySegment":
        assert self._mode == "a"

        for v in range(version+1): # +1 -> Also close last segment in current version
            entry = self._find_open_segment(v)
            if entry is not None:
                self._close_segment(entry[0], from_timestamp)

        segment = ReplaySegment(bytearray(), version, game_id=game_id, player_id=player_id,
                                max_patches=DEFAULT_MAX_PATCHES)
        segment.collapse_all()
        segment.load_everything()
        self.segments[(from_timestamp, None, version)] = segment
        return segment

    def _extend_segment(self, segment: "ReplaySegment") -> None:
        assert self._mode == "a"
        new_max_patches = segment.storage.metadata.current_patches * 2
        segment.collapse_all()
        segment.set_max_patches(new_max_patches)
        segment.load_append_mode()


