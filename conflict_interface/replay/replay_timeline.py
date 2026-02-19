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
        segment = self._find_last_version_entry(version)[1]
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

    def _find_last_version_entry(self, version) -> tuple:
        """
        Find last segment for specific version

        Args:
            version: the version to serach for

        Returns: Open key value pair entry from self.segments with the correct version

        """
        for (from_ts, to_ts, v), segment in self.segments.items():
            if version == v:
                if to_ts is None:
                    return (from_ts, to_ts, v), segment
        return None, None

    def _create_segment(self, version: int, from_timestamp: datetime, game_id: int, player_id: int):
        assert self._mode == "a"
        # -- Close Last Segment --
        last_entry = self._find_last_version_entry(version)
        if last_entry != (None, None):
            closed_entry = (last_entry[0][0], from_timestamp, version)
            self.segments[closed_entry] = last_entry[1]
            self.segments.pop(last_entry[0])
        # -- Create new segment -- 
        segment = ReplaySegment(bytearray([]),version,  game_id=game_id, player_id=player_id, max_patches= DEFAULT_MAX_PATCHES)
        segment.collapse_all()
        segment.load_everything()
        self.segments[(from_timestamp, None, version)] = segment
        return segment

    def _extend_segment(self, segment):
        assert self._mode == "a"
        new_max_patches = segment.storage.metadata.current_patches*2
        segment.collapse_all()
        segment.set_max_patches(new_max_patches)
        segment.load_append_mode()



