"""Shared data structures for the replay health check."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import StrEnum
from pathlib import Path


class Status(StrEnum):
    OK = "OK"
    DEGRADED = "DEGRADED"
    FAILED = "FAILED"


class FailureCategory(StrEnum):
    FILE_NOT_FOUND = "FILE_NOT_FOUND"
    NOT_A_REPLAY = "NOT_A_REPLAY"
    UNSUPPORTED_CONTAINER_VERSION = "UNSUPPORTED_CONTAINER_VERSION"
    VERSION_INCOMPATIBLE = "VERSION_INCOMPATIBLE"
    STRUCTURALLY_CORRUPTED = "STRUCTURALLY_CORRUPTED"
    CORRUPTED_SEGMENT = "CORRUPTED_SEGMENT"
    UNEXPECTED_ERROR = "UNEXPECTED_ERROR"


@dataclass
class ReplayRow:
    """A single discovered replay file, before analysis."""
    game_id: int | None
    player_id: int | None
    path: Path


@dataclass
class ReplayHealth:
    """Full per-replay analysis result."""

    game_id: int | None
    player_id: int | None
    name: str

    status: Status = Status.OK
    failure_category: FailureCategory | None = None
    failure_detail: str | None = None
    # "none" | "metadata_only" | "full" — how far analysis got before either
    # finishing or being limited by missing static map data (not a defect).
    parse_depth: str = "none"
    degraded_reasons: list[str] = field(default_factory=list)

    # Stage 1 — metadata (read_metadata mode, always attempted)
    segment_count: int | None = None
    patches: int | None = None
    map_id: str | None = None
    seg_first_ts: datetime | None = None
    seg_last_ts: datetime | None = None

    # Stage 2 — version compatibility
    required_versions: set[int] = field(default_factory=set)
    unsupported_versions: set[int] = field(default_factory=set)

    # Stage 4 — full parse (game_info_state / newspaper_state / map_state)
    start_of_game: datetime | None = None
    end_of_game: datetime | None = None
    day_first: int | None = None
    day_last: int | None = None
    time_scale: float | None = None
    game_ended: bool | None = None
    ranking_initialized: bool | None = None
    province_ids: set[int] | None = None
    expected_province_ids: set[int] | None = None

    # Stage 4 — player validation
    player_count: int | None = None
    real_player_count: int | None = None
    has_real_players: bool | None = None
    invalid_activity_state_count: int | None = None

    # Stage 4 — coverage / gaps
    n_timestamps: int | None = None
    typical_interval: timedelta | None = None
    gap_count: int = 0
    gap_total: timedelta = field(default_factory=lambda: timedelta(0))
    covered_seconds: float | None = None
    gaps: list[tuple[datetime, datetime, float]] = field(default_factory=list)
