import struct
from datetime import datetime
from pathlib import Path
from typing import Literal

import zstandard as zstd

from conflict_interface.logger_config import get_logger
from conflict_interface.replay.replay_patch import BidirectionalReplayPatch
from conflict_interface.replay.replaysegment import ReplaySegment
from conflict_interface.utils.helper import dt_to_ns
from conflict_interface.utils.helper import ns_to_dt

DEFAULT_MAX_PATCHES = 3000

logger = get_logger()

_MAGIC = b"RPLYZSTD"
_VERSION = 1

class ReplayTimeline:
    def __init__(self,file_path: Path, mode: Literal['r', 'a'] = 'r'):
        self._mode: Literal['r','a'] = mode
        self._open = False
        self.file_path = file_path
        self.segments: dict[tuple[datetime, datetime | None, int], ReplaySegment] = {} # [From_ts, To_ts, version] -> segment

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
                    result[key] = ReplaySegment(payload, seg_version)

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

    def _close_segment(self, key: tuple[datetime, datetime | None, int], close_timestamp: datetime) -> None:
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


