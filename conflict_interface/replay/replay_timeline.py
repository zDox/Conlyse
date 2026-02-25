from __future__ import annotations

import json
import pickle
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
from conflict_interface.replay.replaysegment import ReplaySegment
from conflict_interface.utils.helper import dt_to_ns
from conflict_interface.utils.helper import ns_to_dt

if TYPE_CHECKING:
    from conflict_interface.data_types.newest.game_state.game_state import GameState
    from conflict_interface.data_types.newest.static_map_data import StaticMapData

DEFAULT_MAX_PATCHES = 10000

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
        self.latest_version = -1
        self._time_stamp_cache = []

        self.compressor = zstd.ZstdCompressor(level=11)
        self.decompressor = zstd.ZstdDecompressor()

        self.last_time: datetime | None = None

    def read_from_disk(self):
        assert not self._open, "Reading to a Open Timeline is not Supported"

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

    def _write_to_disk(self):
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
        if self.file_path.exists():
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
        self._write_to_disk()
        self._open = False

    def setup(self, game, static_map_data):
        assert self._open, "Must open before setup"
        for (_,_, v), segment in self.segments.items():
            segment.storage.initial_game_state.set_game(game)
            segment.storage.initial_game_state.states.map_state.map.set_static_map_data(static_map_data[v])

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
        key, segment = self._find_open_segment(self.latest_version)
        segment.set_last_game_state(game_state)

    def get_last_game_state(self) -> GameState | None:
        key_segment = self._find_open_segment(self.latest_version)
        if key_segment is None: return None
        key, segment = key_segment
        return segment.get_last_game_state()

    def que_append_patch(self, version :int, to_time_stamp: datetime, replay_patch: BidirectionalReplayPatch | None, current_game_state: GameState | None = None, static_map_data: StaticMapData | None = None):
        assert self._mode == "a"
        segment = self._find_open_segment(version)
        if segment is not None:
            segment = segment[1]
        else:
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

    def find_segment(self, time: datetime):
        for key, segment in self.segments.items():
            if key[0] < time and (key[1] is None or key[1] >= time):
                return segment

        return None


    def find_first_segment(self):
        first = self.find_last_segment().get_last_time()
        first_segment = None
        for key, segment in self.segments.items():
            if key[0] < first:
                first_segment = segment
                first = key[0]
        return first_segment

    def find_last_segment(self):
        last = datetime.fromtimestamp(0, tz=UTC)
        last_segment = None
        for key, segment in self.segments.items():
            if key[0] > last:
                last_segment = segment
                last = key[0]

        return last_segment

    def _find_last_key_segment(self):
        last = datetime.fromtimestamp(0, tz=UTC)
        last_segment = None
        last_key = None
        for key, segment in self.segments.items():
            if key[0] > last:
                last_segment = segment
                last = key[0]
                last_key = key

        return last_key, last_segment

    def _close_segment(self, key: tuple[datetime, datetime | None, int], close_timestamp: datetime) -> None:
        """Close an open segment by replacing its key with a bounded one."""
        from_ts, _, version = key
        segment = self.segments.pop(key)
        self.segments[(from_ts, close_timestamp, version)] = segment

    def close_last_segment(self):
        key, segment = self._find_last_key_segment()

        if segment is not None:
            self._close_segment(key, segment.get_last_time())

    def _create_segment(self, current_game_state: GameState, version: int, from_timestamp: datetime, static_map_data: StaticMapData | None = None) -> "ReplaySegment":
        assert self._mode == "a"
        assert current_game_state is not None, "Had to create a new Segment but got no game state"

        self.close_last_segment()

        segment = ReplaySegment(bytearray(), version, game_id=self.game_id, player_id=self.player_id,
                                max_patches=DEFAULT_MAX_PATCHES)

        segment.set_last_game_state(current_game_state)
        segment.storage.initialize(DEFAULT_MAX_PATCHES)
        segment.record_initial_game_state(current_game_state, from_timestamp, game_id=self.game_id,
                                          player_id=self.player_id)
        if static_map_data is not None:
            segment.record_static_map_data(static_map_data, game_id=self.game_id, player_id=self.player_id)

        segment.collapse_all()
        segment.load_everything()

        self.segments[(from_timestamp, None, version)] = segment
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
            cache.extend([
                datetime.fromtimestamp(x, tz=UTC) for x in segment.storage.patch_graph.time_stamps_cache
            ])
        cache.sort()

        self._time_stamp_cache = cache
        return self._time_stamp_cache

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
        decompressed = zstd.ZstdDecompressor().decompress(compressed_data)
        static_map_data = pickle.loads(decompressed)
        if isinstance(static_map_data, StaticMapData):
            logger.info("Loaded static map data as StaticMapData object")
            return static_map_data
        elif isinstance(static_map_data, dict):
            logger.info("Loaded static map data as dict")
            static_map_data = parser.parse_static_map_data(static_map_data)
            return static_map_data
        else:
            raise ValueError(f"Unexpected static map data type: {type(static_map_data)}")
