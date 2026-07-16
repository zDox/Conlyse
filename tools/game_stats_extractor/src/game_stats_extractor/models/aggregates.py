"""
Pydantic output models for cross-game aggregate statistics (Step 2).
These are serialized to JSON for the Docusaurus statistics page.
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class BuildingTimeSeriesPoint(BaseModel):
    bucket: int
    avg_count: float
    games_sampled: int


class BuildingAggregate(BaseModel):
    upgrade_identifier: str
    games_appeared: int
    avg_per_game: float
    avg_level: float
    avg_per_tier: dict[int, float] = {}


class ProductionTimeSeriesPoint(BaseModel):
    bucket: int
    avg_production: float
    games_sampled: int


class DurationBucket(BaseModel):
    min_days: float
    max_days: float
    count: int


class GlobalAggregate(BaseModel):
    """Section 2.1 — global metrics across all games."""
    total_games: int
    avg_duration_hours: float
    median_duration_hours: float
    std_duration_hours: float
    duration_distribution: list[DurationBucket]
    victory_type_distribution: dict[str, int]
    avg_players_per_game: float
    avg_human_players_per_game: float
    player_count_distribution: dict[str, int]
    avg_dropout_rate: float
    avg_game_days: float
    avg_update_interval_seconds: float
    avg_wars_per_game: float = 0.0
    avg_peace_treaties_per_game: float = 0.0
    avg_alliances_per_game: float = 0.0
    avg_right_of_ways_per_game: float = 0.0
    avg_game_total_production: dict[str, float] = {}
    coalition_size_distribution: dict[str, int] = {}
    avg_coalition_size: float = 0.0
    top_coalition_pairs: list[list[str | int]] = []
    elimination_timing_distribution: dict[str, int] = {}
    total_traitor_wins: int = 0
    traitor_win_rate: float = 0.0


class CountryAggregate(BaseModel):
    """Section 2.2 — per-country aggregate across all games where that country was played."""
    nation_name: str
    games_played: int
    human_games_played: int = 0
    wins: int
    win_rate: float
    avg_final_vp: float
    avg_placement: float
    median_placement: float
    avg_final_provinces: float
    avg_initial_provinces: float
    avg_expansion: float
    avg_provinces_captured: float
    avg_provinces_lost: float
    elimination_rate: float
    avg_survival_days: float
    avg_wars_declared: float = 0.0
    avg_peace_treaties_signed: float = 0.0
    avg_alliances_formed: float = 0.0
    avg_right_of_ways_signed: float = 0.0
    avg_shared_intelligence_signed: float = 0.0
    avg_total_production: dict[str, float] = {}
    avg_production_rate: dict[str, float] = {}
    avg_final_building_counts: dict[str, float] = {}
    avg_final_building_levels: dict[str, float] = {}
    avg_national_morale: float = 0.0
    solo_wins: int = 0
    coalition_wins: int = 0
    coalition_win_rate: float = 0.0
    avg_winning_coalition_size: float = 0.0
    avg_elimination_pct: Optional[float] = None


class ClusterInfo(BaseModel):
    """A KMeans cluster over normalized nation building-composition vectors."""
    id: int
    label: str
    size: int
    top_buildings: list[str] = []


class NationSimilarityAggregate(BaseModel):
    """Section 2.2b — per-nation build-style clustering, restricted to nations with
    enough human-played games to be meaningfully player-controlled."""
    nation_name: str
    games_played: int
    human_games_played: int
    cluster_id: int
    pca_x: float
    pca_y: float
    top_buildings: list[str] = []


class ProvinceAggregate(BaseModel):
    """Section 2.3 — per-province aggregate across all games where that province appeared."""
    province_id: int
    province_name: str
    terrain_type: str
    is_coastal: bool
    region: str
    original_owner_nation: Optional[str] = None
    games_appeared: int
    avg_ownership_changes: float
    contest_frequency: float
    win_correlation: float
    resource_production_type: Optional[str]
    avg_resource_production: float
    avg_money_production: float
    avg_morale: float
    typical_buildings: dict[str, float] = {}
    avg_building_levels: dict[str, float] = {}


class TimeSeriesPoint(BaseModel):
    bucket: int
    avg_provinces: float
    avg_vp: float
    games_sampled: int


class MoraleTimeSeriesPoint(BaseModel):
    bucket: int
    avg_morale: float
    games_sampled: int


class CountryTimeSeries(BaseModel):
    nation_name: str
    games_played: int
    pct_game: list[TimeSeriesPoint]
    game_days: list[TimeSeriesPoint]
    production_pct_game: dict[str, list[ProductionTimeSeriesPoint]] = {}
    production_game_days: dict[str, list[ProductionTimeSeriesPoint]] = {}
    building_pct_game: dict[str, list[BuildingTimeSeriesPoint]] = {}
    morale_pct_game: list[MoraleTimeSeriesPoint] = []
    morale_game_days: list[MoraleTimeSeriesPoint] = []


class PlayerActivityPoint(BaseModel):
    bucket: int
    avg_alive: float
    avg_active_human: float
    avg_passive_human: float
    avg_ai: float
    games_sampled: int


class TimeSeriesOutput(BaseModel):
    countries: list[CountryTimeSeries]
    pct_buckets: list[int]
    max_game_days: int
    generated_at: datetime
    player_activity_pct: list[PlayerActivityPoint] = []
    player_activity_days: list[PlayerActivityPoint] = []


class MetaInfo(BaseModel):
    """Metadata written alongside aggregate JSON files."""
    game_count: int
    failed_replays: int
    generated_at: datetime
    replay_dir: str
    date_range_start: Optional[datetime]
    date_range_end: Optional[datetime]
