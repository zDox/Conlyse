from datetime import datetime
from typing import Literal

from conflict_interface.logger_config import get_logger
from conflict_interface.replay.replay_patch import BidirectionalReplayPatch
from conflict_interface.replay.replaysegment import ReplaySegment

DEFAULT_MAX_PATCHES = 10000

logger = get_logger()

class ReplayTimeline:
    def __init__(self, mode: Literal['r', 'w', 'a', 'rw'] = 'r'):
        self._mode: Literal['r', 'w', 'a', 'rw'] = mode
        self._open = False
        self.segments: dict[tuple[datetime, datetime, int], ReplaySegment] = {} # [From_ts, To_ts, version] -> segment

    def open(self):
        if self._open:
            return
        for segment in self.segments.values():
            segment.open()
        pass

    def close(self):
        if not self._open:
            return
        for segment in self.segments.values():
            segment.close()
        pass

    def get_mode(self):
        return self._mode

    def set_mode(self, mode: Literal['r', 'w', 'a', 'rw'] = 'r'):
        if mode == self._mode:
            return
        if self._open:
            self.close()
            self._mode = mode
            for segment in self.segments.values():
                segment.set_mode(self._mode)
            self.open()
        else:
            self._mode = mode

    def que_append_patch(self, version :int, from_time_stamp: datetime, to_time_stamp: datetime, game_id: int, player_id: int, replay_patch: BidirectionalReplayPatch):
        segment = self.segments.get((from_time_stamp, to_time_stamp, version), None)
        if segment is None:
            segment = self._create_segment(version, from_time_stamp, to_time_stamp, game_id, player_id)

        if segment is None:
            raise Exception(f"Unable to create segment for {version}, {from_time_stamp}-{to_time_stamp}")
        try:
            segment.que_append_patch(to_time_stamp, game_id, player_id, replay_patch)
        except IndexError:
            logger.warning(f"Had to increase max_patches for segment: {version}, {from_time_stamp}-{to_time_stamp}")
            self._extend_segment(segment)
            segment.que_append_patch(to_time_stamp, game_id, player_id, replay_patch)

    def execute_append_que(self):
        for segment in self.segments.values():
            segment.execute_append_que()

    def _create_segment(self, version: int, from_timestamp: datetime, to_timestamp: datetime, game_id: int, player_id: int):
        segment = ReplaySegment(bytearray([]),version,  "w", game_id=game_id, player_id=player_id, max_patches= DEFAULT_MAX_PATCHES)
        segment.open()
        segment.close()
        segment.set_mode(self._mode)
        self.segments[(from_timestamp, to_timestamp, version)] = segment
        return segment

    def _extend_segment(self, segment):
        new_max_patches = segment.storage.metadata.current_patches*2
        segment.close()
        segment.set_mode("rw")
        segment.set_max_patches(new_max_patches)
        segment.open()
        segment.close()
        segment.set_mode(self._mode)
        segment.open()



