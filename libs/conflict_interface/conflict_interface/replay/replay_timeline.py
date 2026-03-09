from __future__ import annotations

import json
import struct
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import Literal
from typing import TYPE_CHECKING

import zstandard as zstd

from conflict_interface.game_object.game_object_parse_json import JsonParser
from conflict_interface.logger_config import get_logger
from conflict_interface.replay.replay_patch import BidirectionalReplayPatch
from conflict_interface.replay.replay_segment import ReplaySegment
from conflict_interface.replay.timeline_metadata import TimelineMetadata
from conflict_interface.utils.helper import dt_to_ns
from conflict_interface.utils.helper import ns_to_dt

if TYPE_CHECKING:
    from conflict_interface.data_types.newest.game_state.game_state import GameState

DEFAULT_MAX_PATCHES = 10000
MAX_STATIC_MAP_DATA_SIZE = 1024 * 1024 * 10 # 10 Mb

logger = get_logger()

_MAGIC = b"RPLYZSTD"
_VERSION = 2


class ReplayTimeline:
    def __init__(self,file_path: Path, mode: Literal['r', 'a', 'read_metadata'] = 'r', game_id = None, player_id= None):
        self._mode: Literal['r','a','read_metadata'] = mode
        self._open = False
        self.file_path = file_path
        # Mapping from (start_time, end_time) -> ReplaySegment.
        # There must never be overlapping intervals; at most one segment may be active at any time.
        self.segments: dict[tuple[datetime, datetime | None], ReplaySegment] = {}
        self.game_id = game_id
        self.player_id = player_id
        self.latest_version = -1
        self._time_stamp_cache = []

        self.compressor = zstd.ZstdCompressor(level=11)
        self.decompressor = zstd.ZstdDecompressor()

        self.last_time: datetime | None = None
        self.timeline_metadata: TimelineMetadata | None = None

    def read_from_disk(self):
        assert not self._open, "Reading to a Open Timeline is not Supported"

        result: dict[tuple[datetime, datetime | None], ReplaySegment] = {}

        dctx = self.decompressor

        with open(self.file_path, "rb") as raw:
            with dctx.stream_reader(source=raw) as reader:

                def read_exact(n: int) -> bytes:
                    data = reader.read(n)
                    if len(data) != n:
                        raise EOFError("Unexpected end of file while reading replay")
                    return data

                def read_or_none(n: int) -> bytes | None:
                    data = reader.read(n)
                    if not data:
                        return None
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

                # Per-timeline metadata header
                meta_bytes = read_exact(TimelineMetadata.size)
                self.timeline_metadata = TimelineMetadata.deserialize(meta_bytes)

                # ---- segments ----
                header_size = struct.calcsize("<qqiQ")
                while True:
                    header = read_or_none(header_size)
                    if header is None:
                        break

                    start_ns, end_ns, seg_version, size = struct.unpack("<qqiQ", header)

                    payload = bytearray(read_exact(size))

                    start_dt = ns_to_dt(start_ns)
                    end_dt = ns_to_dt(end_ns)

                    key = (start_dt, end_dt)
                    result[key] = ReplaySegment(payload, seg_version, game_id=self.game_id, player_id=self.player_id)

        self.segments = result

        # Validate structure and update latest_version based on segments present in the file.
        self._validate_segments_non_overlapping()
        if self.segments:
            self.latest_version = max(segment.version for segment in self.segments.values())
        else:
            self.latest_version = -1

    def _write_to_disk(self):
        cctx = self.compressor
        # Always sort for determinism.
        ordered_items = sorted(self.segments.items(), key=lambda kv: kv[0])

        # Ensure structural invariants before persisting.
        self._validate_segments_non_overlapping()

        # Ensure we have timeline metadata populated
        if self.timeline_metadata is None:
            self.timeline_metadata = TimelineMetadata(
                game_ended=False,
                start_of_game=0,
                end_of_game=0,
                game_id=int(self.game_id) if self.game_id is not None else 0,
                player_id=int(self.player_id) if self.player_id is not None else 0,
                scenario_id=0,
                day_of_game=0,
                speed=0,
                segment_count=len(ordered_items),
            )
        else:
            # Keep segment_count in sync with current segments
            self.timeline_metadata.segment_count = len(ordered_items)

        with open(self.file_path, "wb") as raw:
            with cctx.stream_writer(raw) as compressor:
                # ---- file header ----
                compressor.write(_MAGIC)  # magic
                compressor.write(struct.pack("<I", _VERSION))  # version
                compressor.write(self.timeline_metadata.serialize())

                # ---- segments ----
                for (start, end), segment in ordered_items:
                    payload = segment.get_binary()  # bytearray
                    seg_version = segment.version

                    header = struct.pack(
                        "<qqiQ",
                        dt_to_ns(start),
                        dt_to_ns(end),
                        seg_version,
                        len(payload),
                    )

                    compressor.write(header)
                    compressor.write(payload)

    def open(self):
        if self._open:
            return
        if self.file_path.exists():
            self.read_from_disk()
        if self._mode == "a":
            last_segment = self.find_last_segment()
            if last_segment is not None:
                last_segment.load_append_mode()
        elif self._mode == "r":
            for segment in self.segments.values():
                segment.load_everything()
        elif self._mode == "read_metadata":
            # Only load per-segment metadata; skip heavy structures.
            for segment in self.segments.values():
                segment.storage.read_metadata_from_disk()
                segment.storage.load_metadata()
        self._open = True

    def close(self):
        if not self._open:
            return
        if self._mode == "a":
            for segment in self.segments.values():
                segment.collapse_append_mode()
        self._write_to_disk()
        self._open = False

    def setup(self, game, static_map_data):
        assert self._open, "Must open before setup"
        for (_, _), segment in self.segments.items():
            v = segment.version
            segment.storage.initial_game_state.set_game(game)
            segment.storage.initial_game_state.states.map_state.map.set_static_map_data(static_map_data[v])

    def get_mode(self):
        return self._mode

    def set_mode(self, mode: Literal['r', 'a', 'read_metadata']):
        if mode == self._mode:
            return
        if self._open:
            self.close()
            self._mode = mode
            self.open()
        else:
            self._mode = mode

    def set_last_game_state(self, game_state: GameState):
        key, segment = self._find_open_segment(self.latest_version)
        segment.set_last_game_state(game_state)

    def get_last_game_state(self) -> GameState | None:
        key_segment = self._find_open_segment(self.latest_version)
        if key_segment is None: return None
        key, segment = key_segment
        return segment.get_last_game_state()

    def set_metadata(
        self,
        game_ended: bool,
        start_of_game: datetime | None,
        end_of_game: datetime | None,
        scenario_id: int,
        day_of_game: int | None,
        speed: int,
    ) -> None:
        """
        Set or update the timeline-level metadata for this replay.

        Times are stored as Unix seconds; missing values are encoded as 0.
        """
        def to_unix_seconds(dt: datetime | None) -> int:
            if dt is None:
                return 0
            return int(dt.timestamp())

        start_ts = to_unix_seconds(start_of_game)
        end_ts = to_unix_seconds(end_of_game)
        game_id = int(self.game_id) if self.game_id is not None else 0
        player_id = int(self.player_id) if self.player_id is not None else 0

        if day_of_game is None:
            day_of_game_int = 0
        else:
            day_of_game_int = int(day_of_game)

        segment_count = len(self.segments)

        self.timeline_metadata = TimelineMetadata(
            game_ended=bool(game_ended),
            start_of_game=start_ts,
            end_of_game=end_ts,
            game_id=game_id,
            player_id=player_id,
            scenario_id=int(scenario_id),
            day_of_game=day_of_game_int,
            speed=int(speed),
            segment_count=segment_count,
        )

    def set_day_of_game(self, day_of_game: int) -> None:
        """
        Update only the day_of_game field in the timeline metadata.
        """
        if self.timeline_metadata is not None:
            self.timeline_metadata.day_of_game = int(day_of_game)

    def set_game_ended(self, game_ended: bool) -> None:
        if self.timeline_metadata is not None:
            self.timeline_metadata.game_ended = bool(game_ended)

    def set_game_end(self, game_end: datetime | None) -> None:
        if self.timeline_metadata is not None:
            self.timeline_metadata.end_of_game = int(game_end.timestamp()) if game_end is not None else 0

    def que_append_patch(self, version :int, to_time_stamp: datetime, replay_patch: BidirectionalReplayPatch | None, current_game_state: GameState | None = None, map_id: str | None = None):
        assert self._mode == "a"
        segment = self._find_open_segment(version)
        if segment is not None:
            segment = segment[1]
        else:
            segment = self._create_segment(
                current_game_state,
                version,
                self.last_time,
                map_id=map_id,
            )

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
            (
                (key, seg)
                for (key, seg) in self.segments.items()
                if key[1] is None and seg.version == version
            ),
            None
        )

    def find_segment(self, time: datetime):
        for key, segment in self.segments.items():
            start, end = key
            if start < time and (end is None or end >= time):
                return segment

        return None


    def find_first_segment(self):
        first = self.find_last_segment().get_last_time()
        first_segment = None
        for key, segment in self.segments.items():
            start, _ = key
            if start < first:
                first_segment = segment
                first = start
        return first_segment

    def find_last_segment(self):
        last = datetime.fromtimestamp(0, tz=UTC)
        last_segment = None
        for key, segment in self.segments.items():
            start, _ = key
            if start > last:
                last_segment = segment
                last = start

        return last_segment

    def _find_last_key_segment(self):
        last = datetime.fromtimestamp(0, tz=UTC)
        last_segment = None
        last_key = None
        for key, segment in self.segments.items():
            start, _ = key
            if start > last:
                last_segment = segment
                last = start
                last_key = key

        return last_key, last_segment

    def _close_segment(self, key: tuple[datetime, datetime | None, int], close_timestamp: datetime) -> None:
        """Close an open segment by replacing its key with a bounded one."""
        from_ts, _ = key
        segment = self.segments.pop(key)
        self.segments[(from_ts, close_timestamp)] = segment

    def close_last_segment(self):
        key, segment = self._find_last_key_segment()

        if segment is not None:
            self._close_segment(key, segment.get_last_time())

    def _validate_segments_non_overlapping(self) -> None:
        """
        Ensure that there is at most one segment covering any point in time.

        Segments are defined by half-open intervals [start, end] where end may be None
        for an open-ended segment. After sorting by start time, no segment is allowed
        to start before the previous one has ended.
        """
        if not self.segments:
            return

        # Sort by (start, end) so we can check neighbors for overlap.
        ordered_keys = sorted(self.segments.keys(), key=lambda k: (k[0], k[1]))

        prev_start, prev_end = ordered_keys[0]
        for start, end in ordered_keys[1:]:
            # If previous segment is open-ended, any later segment would overlap.
            if prev_end is None:
                raise ValueError(
                    f"Overlapping replay segments detected: open segment starting at {prev_start} "
                    f"overlaps with segment starting at {start}."
                )
            # Otherwise, the next segment must not start before previous end.
            if start < prev_end:
                raise ValueError(
                    f"Overlapping replay segments detected: segment [{prev_start}, {prev_end}] "
                    f"overlaps with [{start}, {end}]."
                )
            prev_start, prev_end = start, end

    def _create_segment(self, current_game_state: GameState, version: int, from_timestamp: datetime, map_id: str | None = None) -> "ReplaySegment":
        assert self._mode == "a"
        assert current_game_state is not None, "Had to create a new Segment but got no game state"

        self.close_last_segment()

        segment = ReplaySegment(bytearray(), version, game_id=self.game_id, player_id=self.player_id,
                                max_patches=DEFAULT_MAX_PATCHES)

        segment.set_last_game_state(current_game_state)
        segment.storage.initialize(DEFAULT_MAX_PATCHES)
        if map_id is not None:
            segment.storage.metadata.map_id = map_id
        segment.record_initial_game_state(current_game_state, from_timestamp, game_id=self.game_id,
                                          player_id=self.player_id)

        segment.collapse_all()
        segment.load_everything()

        self.segments[(from_timestamp, None)] = segment
        self._time_stamp_cache = []
        return segment

    def _extend_segment(self, segment: "ReplaySegment") -> None:
        assert self._mode == "a"
        new_max_patches = segment.storage.metadata.current_patches * 2
        segment.collapse_all()
        segment.set_max_patches(new_max_patches)
        segment.load_append_mode()

    def set_game(self, game):
        for key, segment in self.segments.items():
            segment.set_game(game=game)

    def get_start_time(self):
        return self.find_first_segment().get_start_time()

    def get_last_time(self):
        return self.find_last_segment().get_last_time()

    def get_timestamp_cache(self):
        if self._time_stamp_cache:
            return self._time_stamp_cache
        cache = []
        for key, segment in self.segments.items():
            cache.extend(
                [
                    datetime.fromtimestamp(x, tz=UTC)
                    for x in segment.storage.patch_graph.time_stamps_cache
                ]
            )
        cache.sort()

        self._time_stamp_cache = cache
        return self._time_stamp_cache

    def get_segments_metadata(self) -> dict[tuple[datetime, datetime | None], "Metadata"]:
        """
        Return a mapping from segment time-interval keys to their loaded Metadata objects.

        This assumes metadata has already been loaded (either via full open() or
        metadata-only mode).
        """
        from conflict_interface.replay.segment_metadata import SegmentMetadata

        result: dict[tuple[datetime, datetime | None], SegmentMetadata] = {}
        for key, segment in self.segments.items():
            if segment.storage.metadata is not None:
                result[key] = segment.storage.metadata
        return result

    def get_timeline_metadata(self) -> TimelineMetadata | None:
        """
        Return the timeline-level metadata for this replay, if available.
        """
        return self.timeline_metadata


    @staticmethod
    def read_static_map_data(version, path):
        parser = JsonParser(version)
        parser.type_graph.build_graph()
        if not path.exists():
            logger.warning(f"Static map data file not found: {path}")
            return None

        # If the static map data is stored as JSON, read it in text mode and parse directly.
        if path.suffix == ".json":
            with open(path, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
            return parser.parse_static_map_data(json_data)

        # Otherwise, assume the file contains compressed binary data.
        with open(path, 'rb') as f:
            compressed_data = f.read()

        # Decompress and unpickle
        decompressed = zstd.ZstdDecompressor().decompress(compressed_data, max_output_size=MAX_STATIC_MAP_DATA_SIZE)
        json_data = json.loads(decompressed)

        return parser.parse_static_map_data(json_data)
