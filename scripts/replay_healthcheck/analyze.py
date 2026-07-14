"""Staged per-replay health analysis.

Each stage only runs if the previous one succeeded. A failure at any stage
stops further stages and returns a FAILED result with a specific
FailureCategory + detail message, instead of a single generic
`except Exception` bucket.
"""

import statistics
from datetime import timedelta

from conflict_interface.interface.replay_interface import ReplayInterface

from .compat import unsupported_versions
from .models import FailureCategory, ReplayHealth, ReplayRow, Status

# A delta between consecutive recorded timestamps larger than
# GAP_FACTOR * (median delta for that replay) is treated as a recording gap.
GAP_FACTOR = 4.25

_VALID_ACTIVITY_STATES = {"ACTIVE", "UNKNOWN", "INACTIVE", "ABANDONED"}


def _fail(r: ReplayHealth, category: FailureCategory, detail: str) -> ReplayHealth:
    r.status = Status.FAILED
    r.failure_category = category
    r.failure_detail = detail
    return r


def _classify_parse_error(msg: str) -> FailureCategory:
    """Classify an exception raised during a full parse by message content.

    `GameObjectSerializer._from_raw_registered` raises a raw, unwrapped
    "Unknown type_id ..." KeyError when a replay's embedded objects use a
    finer-grained type that isn't registered for its GameState version — a
    real schema-version mismatch that Stage 2's coarse whole-version check
    (get_required_versions() vs get_supported_datatype_versions()) can't
    catch, since the outer GameState version itself may still be "supported"
    even though a specific object type within it isn't.
    """
    if "lz4 decompression failed" in msg:
        return FailureCategory.CORRUPTED_SEGMENT
    if "Unknown type_id" in msg:
        return FailureCategory.VERSION_INCOMPATIBLE
    return FailureCategory.UNEXPECTED_ERROR


def analyze_one(row: ReplayRow, static_map_data: dict) -> ReplayHealth:
    """Run the staged health analysis for a single replay file.

    Runs in a worker process — must be picklable/standalone.
    """
    path = row.path
    name = path.stem
    r = ReplayHealth(game_id=row.game_id, player_id=row.player_id, name=name)

    # Stage 0 — existence
    if not path.exists():
        return _fail(r, FailureCategory.FILE_NOT_FOUND, f"{path} does not exist")

    # Stage 1 — metadata open (cheap, no static map data needed)
    try:
        ri = ReplayInterface(path)
        ri.open(mode="read_metadata")
    except ValueError as e:
        msg = str(e)
        if "Unsupported replay format version" in msg:
            return _fail(r, FailureCategory.UNSUPPORTED_CONTAINER_VERSION, msg)
        if "magic" in msg.lower():
            return _fail(r, FailureCategory.NOT_A_REPLAY, msg)
        return _fail(r, FailureCategory.UNEXPECTED_ERROR, msg)
    except Exception as e:
        return _fail(r, FailureCategory.UNEXPECTED_ERROR, str(e))

    try:
        meta = ri.get_timeline_metadata()
        if meta is not None:
            r.segment_count = meta.segment_count
        r.patches = ri.get_total_patches()
        r.seg_last_ts = ri.last_time
        required_map_ids = ri.get_required_map_ids()
        for (start_dt, _), seg in ri._replay.segments.items():
            r.seg_first_ts = start_dt
            m = seg.storage.metadata
            if m:
                r.map_id = m.map_id
            break
        r.parse_depth = "metadata_only"
    except Exception as e:
        ri.close()
        return _fail(r, FailureCategory.UNEXPECTED_ERROR, str(e))

    # Stage 2 — version compatibility (avoids a raw KeyError mid-parse for
    # replays recorded with a datatype version this build doesn't support)
    r.required_versions = ri.get_required_versions()
    r.unsupported_versions = unsupported_versions(r.required_versions)
    if r.unsupported_versions:
        ri.close()
        return _fail(
            r,
            FailureCategory.VERSION_INCOMPATIBLE,
            f"datatype version(s) {sorted(r.unsupported_versions)} not supported by this "
            f"build (replay requires: {sorted(r.required_versions)})",
        )

    ri.close()

    # Stage 3 — structural integrity. This needs each segment's patch tree
    # deserialized (read_metadata mode never reads the path-tree bytes off
    # disk at all — only a full open does), so it can only run as part of
    # the full parse below, not as a cheap metadata-only pre-check.

    # Stage 4 — full parse. Only attempted if static map data covers every
    # map_id this replay requires; otherwise this is an environment
    # limitation (no map data supplied), not a defect in the replay itself,
    # so we leave parse_depth at "metadata_only" and status at OK.
    if not required_map_ids or not required_map_ids.issubset(static_map_data.keys()):
        return r

    try:
        ri = ReplayInterface(path, static_map_data=static_map_data)
        ri.open(mode="r")
    except Exception as e:
        msg = str(e)
        return _fail(r, _classify_parse_error(msg), msg)

    try:
        for segment in ri._replay.segments.values():
            segment.validate_structure()
    except Exception as e:
        ri.close()
        return _fail(r, FailureCategory.STRUCTURALLY_CORRUPTED, str(e))

    try:
        timestamps = ri.get_timestamps()
        ri.jump_to(timestamps[0])
        gi = ri.game_state.states.game_info_state
        r.start_of_game = gi.start_of_game
        r.day_first = gi.day_of_game
        r.time_scale = gi.time_scale

        ri.jump_to(ri.last_time)
        gi = ri.game_state.states.game_info_state
        r.day_last = gi.day_of_game
        r.game_ended = gi.game_ended
        r.end_of_game = gi.end_of_game

        ranking = ri.game_state.states.newspaper_state.ranking
        r.ranking_initialized = ranking.initialized if ranking is not None else None

        map_obj = ri.game_state.states.map_state.map
        r.province_ids = set(map_obj.provinces.keys())
        static = getattr(map_obj, "static_map_data", None)
        if static is not None:
            r.expected_province_ids = set(static.province_to_location.keys())

        players = ri.game_state.states.player_state.players
        r.player_count = len(players)
        real_players = [
            p for p in players.values()
            if not (p.computer_player or p.native_computer or p.terrorist_country)
        ]
        r.real_player_count = len(real_players)
        r.has_real_players = r.real_player_count > 0
        # `None` is the overwhelmingly common value here in practice (this field
        # appears to only be meaningfully populated for the recording player's
        # own POV, not for every player in the game) — only count genuinely
        # unexpected non-None values as invalid, not the common None case.
        r.invalid_activity_state_count = sum(
            1 for p in players.values()
            if p.activity_state is not None and p.activity_state not in _VALID_ACTIVITY_STATES
        )

        r.n_timestamps = len(timestamps)
        if len(timestamps) >= 2:
            deltas = [
                (timestamps[i + 1] - timestamps[i]).total_seconds()
                for i in range(len(timestamps) - 1)
            ]
            typical = statistics.median(deltas)
            gap_threshold = typical * GAP_FACTOR
            normal = [d for d in deltas if d <= gap_threshold]
            gap_intervals = [
                (timestamps[i], timestamps[i + 1], deltas[i])
                for i in range(len(deltas))
                if deltas[i] > gap_threshold
            ]
            r.typical_interval = timedelta(seconds=typical)
            r.gap_count = len(gap_intervals)
            r.gap_total = timedelta(seconds=sum(d for *_, d in gap_intervals))
            r.covered_seconds = sum(normal) + typical
            r.gaps = gap_intervals

        ri.close()
        r.parse_depth = "full"
    except Exception as e:
        msg = str(e)
        return _fail(r, _classify_parse_error(msg), msg)

    # Final status / degraded-reasons rollup
    reasons: list[str] = []
    if not r.game_ended:
        reasons.append("game_not_ended")
    if r.ranking_initialized is not True:
        reasons.append("ranking_not_initialized")
    if r.expected_province_ids is not None and r.province_ids != r.expected_province_ids:
        reasons.append("provinces_missing")
    if r.gap_count > 0:
        reasons.append("has_recording_gaps")
    if not r.has_real_players:
        reasons.append("no_real_players")
    if r.invalid_activity_state_count:
        reasons.append("invalid_player_activity_state")

    r.degraded_reasons = reasons
    r.status = Status.DEGRADED if reasons else Status.OK
    return r


def analyze_replays(rows: list[ReplayRow], static_map_data: dict, workers: int) -> list[ReplayHealth]:
    from concurrent.futures import ProcessPoolExecutor

    from tqdm import tqdm

    results: list[ReplayHealth] = []
    with ProcessPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(analyze_one, row, static_map_data) for row in rows]
        for fut in tqdm(futures, desc="Analysing replays", unit="replay"):
            results.append(fut.result())

    return results
