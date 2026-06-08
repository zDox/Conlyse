"""
Intermediate per-game data structures (not serialized — used only as pipeline input to aggregators).
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class PlayerData:
    player_id: int
    nation_name: str
    player_name: str
    team_id: int
    is_ai: bool
    is_defeated: bool
    is_playing: bool
    final_vp: int
    initial_province_count: int
    final_province_count: int
    max_province_count: int
    min_province_count: int
    avg_province_count: float
    provinces_captured: int = 0
    provinces_lost: int = 0
    pct_buckets: dict[int, int] = field(default_factory=dict)
    day_buckets: dict[int, int] = field(default_factory=dict)
    pct_vp_buckets: dict[int, int] = field(default_factory=dict)
    day_vp_buckets: dict[int, int] = field(default_factory=dict)
    wars_declared: int = 0
    peace_treaties_signed: int = 0
    alliances_formed: int = 0
    alliance_dissolutions: int = 0
    right_of_ways_signed: int = 0
    avg_production_by_type: dict[str, float] = field(default_factory=dict)
    total_production_by_type: dict[str, float] = field(default_factory=dict)
    peak_production_by_type: dict[str, float] = field(default_factory=dict)
    production_pct_buckets: dict[str, dict[int, float]] = field(default_factory=dict)
    production_day_buckets: dict[str, dict[int, float]] = field(default_factory=dict)
    final_building_counts: dict[str, int] = field(default_factory=dict)
    final_building_levels: dict[str, float] = field(default_factory=dict)
    final_building_tier_counts: dict[str, dict[int, int]] = field(default_factory=dict)
    building_pct_buckets: dict[str, dict[int, float]] = field(default_factory=dict)
    building_type_pct_buckets: dict[tuple[str, int], dict[int, float]] = field(default_factory=dict)
    pct_bucket_coverage: dict[int, int] = field(default_factory=dict)
    elimination_game_pct: Optional[float] = None  # 0-100 raw %, None if not eliminated
    elimination_game_day: Optional[int] = None
    avg_national_morale: float = 0.0
    morale_pct_buckets: dict[int, float] = field(default_factory=dict)
    morale_day_buckets: dict[int, float] = field(default_factory=dict)


@dataclass
class ProvinceData:
    province_id: int
    province_name: str
    terrain_type: str
    is_coastal: bool
    initial_owner_id: int
    final_owner_id: int
    ownership_changes: int
    resource_production_type: Optional[str]
    resource_production: int
    money_production: int
    avg_morale: float
    min_morale: float
    max_morale: float
    final_upgrade_counts: dict[str, int] = field(default_factory=dict)


@dataclass
class GameData:
    game_id: int
    map_id: str
    file_path: str
    start_time: datetime
    end_time: datetime
    game_days: int
    total_updates: int
    avg_update_interval_seconds: float
    winner_ids: list[int]
    victory_type: str  # "solo", "coalition", "unknown"
    game_ended: bool
    players: list[PlayerData] = field(default_factory=list)
    provinces: list[ProvinceData] = field(default_factory=list)
    total_wars_declared: int = 0
    total_peace_treaties: int = 0
    total_alliances_formed: int = 0
    total_alliance_dissolutions: int = 0
    total_right_of_ways: int = 0
    pct_alive_buckets: dict[int, int] = field(default_factory=dict)
    pct_active_human_buckets: dict[int, int] = field(default_factory=dict)
    pct_passive_human_buckets: dict[int, int] = field(default_factory=dict)
    pct_ai_buckets: dict[int, int] = field(default_factory=dict)
    day_alive_buckets: dict[int, int] = field(default_factory=dict)
    day_active_human_buckets: dict[int, int] = field(default_factory=dict)
    day_passive_human_buckets: dict[int, int] = field(default_factory=dict)
    day_ai_buckets: dict[int, int] = field(default_factory=dict)
    game_total_production: dict[str, float] = field(default_factory=dict)
