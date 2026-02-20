from __future__ import annotations

import struct
from datetime import datetime
from pathlib import Path
from typing import Literal
from typing import TYPE_CHECKING

import zstandard as zstd

from conflict_interface.game_object.game_object import GameObject
from conflict_interface.interface import GameInterface
from conflict_interface.interface import ReplayInterface
from conflict_interface.logger_config import get_logger
from conflict_interface.replay.replay_patch import BidirectionalReplayPatch
from conflict_interface.replay.replaysegment import ReplaySegment
from conflict_interface.utils.helper import dt_to_ns
from conflict_interface.utils.helper import ns_to_dt

if TYPE_CHECKING:
    from conflict_interface.data_types.newest.game_state.game_state import GameState
    from conflict_interface.data_types.newest.static_map_data import StaticMapData

DEFAULT_MAX_PATCHES = 3000

logger = get_logger()

_MAGIC = b"RPLYZSTD"
_VERSION = 1

class ReplayTimeline:
    def __init__(self,file_path: Path, mode: Literal['r', 'a'] = 'r', game_id = None, player_id= None):
        self._mode: Literal['r','a'] = mode
        self._open = False
        self.file_path = file_path
        self.segments: dict[tuple[datetime, datetime | None, int], ReplaySegment] = {} # [From_ts, To_ts, version] -> segment
        self.game_id = game_id
        self.player_id = player_id

        self.compressor = zstd.ZstdCompressor(level=11)
        self.decompressor = zstd.ZstdDecompressor()

        self.last_time: datetime | None = None

    def read_from_disk(self):
        assert not self.open(), "Reading to a Open Timeline is not Supported"

        result: dict[tuple[datetime, datetime | None, int], ReplaySegment] = {}

        dctx = self.decompressor

        with open(self.file_path, "rb") as raw:
            with dctx.stream_reader(source=raw) as reader:

                def read_exact(n: int) -> bytes:
                    data = reader.read(n)
                    if len(data) != n:
                        raise EOFError("Unexpected end of file while reading replay")
                    return data

                # ---- file header ----
                magic = read_exact(len(_MAGIC))
                if magic != _MAGIC:
                    raise ValueError("Not a replay zstd file (bad magic)")

                (version,) = struct.unpack("<I", read_exact(4))
                if version != _VERSION:
                    raise ValueError(f"Unsupported file version: {version}")

                (count,) = struct.unpack("<Q", read_exact(8))

                # ---- segments ----
                for _ in range(count):
                    start_ns, end_ns, seg_version, size = struct.unpack(
                        "<qqiQ", read_exact(struct.calcsize("<qqiQ"))
                    )

                    payload = bytearray(read_exact(size))

                    start_dt = ns_to_dt(start_ns)
                    end_dt = ns_to_dt(end_ns)

                    key = (start_dt, end_dt, seg_version)
                    result[key] = ReplaySegment(payload, seg_version, game_id = self.game_id , player_id = self.player_id)

        self.segments =result

    def write_to_disk(self):
        assert not self.open(), "Writing a Open Timeline is not Supported"

        cctx = self.compressor
        # Always sort for determinism.
        ordered_items = sorted(self.segments.items(), key=lambda kv: kv[0])

        with open(self.file_path, "wb") as raw:
            with cctx.stream_writer(raw) as compressor:
                # ---- file header ----
                compressor.write(_MAGIC)  # magic
                compressor.write(struct.pack("<I", _VERSION))  # version
                compressor.write(struct.pack("<Q", len(ordered_items)))

                # ---- segments ----
                for (start, end, idx), segment in ordered_items:
                    payload = segment.get_binary()  # bytearray

                    header = struct.pack(
                        "<qqiQ",
                        dt_to_ns(start),
                        dt_to_ns(end),
                        idx,
                        len(payload),
                    )

                    compressor.write(header)
                    compressor.write(payload)

    def open(self):
        if self._open:
            return
        self.read_from_disk()
        if self._mode == "a":
            for segment in self.segments.values():
                segment.load_append_mode()
        elif self._mode == "r":
            for segment in self.segments.values():
                segment.load_everything()
        self._open = True

    def close(self):
        if not self._open:
            return
        if self._mode == "a":
            for segment in self.segments.values():
                segment.collapse_append_mode()
        self.write_to_disk()
        self._open = False

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

    def set_last_game_state(self, game_state: GameState):
        pass

    def get_last_game_state(self) -> GameState:
        pass

    def que_append_patch(self, version :int, to_time_stamp: datetime, replay_patch: BidirectionalReplayPatch | None, current_game_state: GameState | None = None, static_map_data: StaticMapData | None = None):
        assert self._mode == "a"
        segment = self._find_open_segment(version)[1]
        if segment is None:
            segment = self._create_segment(current_game_state,
                                           version,
                                           self.last_time,
                                           static_map_data=static_map_data)

        if segment is None:
            raise Exception(f"Unable to create last segment in version: {version}")
        for i in range(2):
            try:
                segment.que_append_patch(to_time_stamp,
                                         self.game_id,
                                         self.player_id,
                                         replay_patch)
                break
            except IndexError: # TODO make custom execption
                logger.warning(f"Had to increase max_patches for last segment in version: {version}")
                self._extend_segment(segment)

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

    def _close_segment(self, key: tuple[datetime, datetime | None, int], close_timestamp: datetime) -> None:
        """Close an open segment by replacing its key with a bounded one."""
        from_ts, _, version = key
        segment = self.segments.pop(key)
        self.segments[(from_ts, close_timestamp, version)] = segment

    def _create_segment(self, current_game_state: GameState, version: int, from_timestamp: datetime, static_map_data: StaticMapData | None = None) -> "ReplaySegment":
        assert self._mode == "a"
        assert current_game_state is not None, "Had to create a new Segment but got no game state"

        for v in range(version+1): # +1 -> Also close last segment in current version
            entry = self._find_open_segment(v)
            if entry is not None:
                self._close_segment(entry[0], from_timestamp)

        segment = ReplaySegment(bytearray(), version, game_id=self.game_id, player_id=self.player_id,
                                max_patches=DEFAULT_MAX_PATCHES)
        segment.record_initial_game_state(current_game_state,from_timestamp, game_id=self.game_id, player_id = self.player_id)
        segment.record_static_map_data(static_map_data, game_id = self.game_id, player_id=self.player_id)

        segment.set_last_game_state(current_game_state)
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


