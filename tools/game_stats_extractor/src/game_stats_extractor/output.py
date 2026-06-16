"""Serializes aggregate models to JSON files in the output directory."""
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from .models.aggregates import BuildingAggregate, CountryAggregate, GlobalAggregate, MetaInfo, ProvinceAggregate, TimeSeriesOutput
from .models.intermediate import GameData


def _default(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def _r(v) -> float | int:
    return round(v, 2) if isinstance(v, float) else v


def _rp(v) -> float:
    """Higher-precision rounding for proportion/rate fields used in scatter plots."""
    return round(v, 4)


def _provinces_columnar(provinces: list[ProvinceAggregate]) -> dict:
    cols = [
        "province_id", "province_name", "terrain_type", "is_coastal",
        "games_appeared", "avg_ownership_changes", "contest_frequency",
        "win_correlation", "resource_production_type",
        "avg_resource_production", "avg_money_production", "avg_morale",
        "typical_buildings",
    ]
    rows = [
        [
            p.province_id, p.province_name, p.terrain_type, p.is_coastal,
            p.games_appeared, _r(p.avg_ownership_changes), _rp(p.contest_frequency),
            _rp(p.win_correlation), p.resource_production_type,
            _r(p.avg_resource_production), _r(p.avg_money_production), _r(p.avg_morale),
            {k: _rp(v) for k, v in p.typical_buildings.items()},
        ]
        for p in provinces
    ]
    return {"columns": cols, "rows": rows}


def _countries_columnar(countries: list[CountryAggregate]) -> dict:
    cols = [
        "nation_name", "games_played", "wins", "win_rate", "avg_final_vp",
        "avg_placement", "median_placement", "avg_final_provinces",
        "avg_initial_provinces", "avg_expansion", "avg_provinces_captured",
        "avg_provinces_lost", "elimination_rate", "avg_survival_days",
        "avg_wars_declared", "avg_peace_treaties_signed",
        "avg_alliances_formed", "avg_right_of_ways_signed",
        "avg_shared_intelligence_signed",
        "avg_total_production", "avg_production_rate",
        "avg_final_building_counts", "avg_final_building_levels",
        "avg_national_morale",
        "solo_wins", "coalition_wins", "coalition_win_rate", "avg_winning_coalition_size",
        "avg_elimination_pct",
    ]
    rows = [
        [
            c.nation_name, c.games_played, c.wins, _r(c.win_rate), _r(c.avg_final_vp),
            _r(c.avg_placement), _r(c.median_placement), _r(c.avg_final_provinces),
            _r(c.avg_initial_provinces), _r(c.avg_expansion),
            _r(c.avg_provinces_captured), _r(c.avg_provinces_lost),
            _r(c.elimination_rate), _r(c.avg_survival_days),
            _r(c.avg_wars_declared), _r(c.avg_peace_treaties_signed),
            _r(c.avg_alliances_formed), _r(c.avg_right_of_ways_signed),
            _r(c.avg_shared_intelligence_signed),
            {k: _r(v) for k, v in c.avg_total_production.items()},
            {k: _r(v) for k, v in c.avg_production_rate.items()},
            {k: _r(v) for k, v in c.avg_final_building_counts.items()},
            {k: _r(v) for k, v in c.avg_final_building_levels.items()},
            _r(c.avg_national_morale),
            c.solo_wins, c.coalition_wins, _r(c.coalition_win_rate), _r(c.avg_winning_coalition_size),
            _r(c.avg_elimination_pct) if c.avg_elimination_pct is not None else None,
        ]
        for c in countries
    ]
    return {"columns": cols, "rows": rows}


def _timeseries_compact(ts: TimeSeriesOutput) -> dict:
    n_days = ts.max_game_days + 1
    countries = []
    for c in ts.countries:
        pct_by_bucket = {p.bucket: p for p in c.pct_game}
        day_by_bucket = {p.bucket: p for p in c.game_days}
        pct_avg    = [_r(pct_by_bucket[b].avg_provinces) if b in pct_by_bucket else None for b in ts.pct_buckets]
        pct_n      = [pct_by_bucket[b].games_sampled if b in pct_by_bucket else None for b in ts.pct_buckets]
        pct_vp_avg = [_r(pct_by_bucket[b].avg_vp) if b in pct_by_bucket else None for b in ts.pct_buckets]
        day_avg    = [_r(day_by_bucket[d].avg_provinces) if d in day_by_bucket else None for d in range(n_days)]
        day_n      = [day_by_bucket[d].games_sampled if d in day_by_bucket else None for d in range(n_days)]
        day_vp_avg = [_r(day_by_bucket[d].avg_vp) if d in day_by_bucket else None for d in range(n_days)]

        prod_pct: dict = {}
        for rtype, points in c.production_pct_game.items():
            by_b = {p.bucket: p for p in points}
            prod_pct[rtype] = {
                "avg": [_r(by_b[b].avg_production) if b in by_b else None for b in ts.pct_buckets],
                "n":   [by_b[b].games_sampled if b in by_b else None for b in ts.pct_buckets],
            }

        prod_day: dict = {}
        for rtype, points in c.production_game_days.items():
            by_b = {p.bucket: p for p in points}
            prod_day[rtype] = {
                "avg": [_r(by_b[d].avg_production) if d in by_b else None for d in range(n_days)],
                "n":   [by_b[d].games_sampled if d in by_b else None for d in range(n_days)],
            }

        bld_pct: dict = {}
        for uid, points in c.building_pct_game.items():
            by_b = {p.bucket: p for p in points}
            bld_pct[uid] = {
                "avg": [_r(by_b[b].avg_count) if b in by_b else None for b in ts.pct_buckets],
                "n":   [by_b[b].games_sampled if b in by_b else None for b in ts.pct_buckets],
            }

        bld_type_pct: dict = {}
        for uid, tiers in c.building_type_pct_game.items():
            bld_type_pct[uid] = {}
            for tier, points in tiers.items():
                by_b = {p.bucket: p for p in points}
                bld_type_pct[uid][tier] = {
                    "avg": [_r(by_b[b].avg_count) if b in by_b else None for b in ts.pct_buckets],
                    "n":   [by_b[b].games_sampled if b in by_b else None for b in ts.pct_buckets],
                }

        morale_pct_by_b = {p.bucket: p for p in c.morale_pct_game}
        morale_day_by_b = {p.bucket: p for p in c.morale_game_days}
        morale_pct_avg = [_r(morale_pct_by_b[b].avg_morale) if b in morale_pct_by_b else None for b in ts.pct_buckets]
        morale_pct_n   = [morale_pct_by_b[b].games_sampled if b in morale_pct_by_b else None for b in ts.pct_buckets]
        morale_day_avg = [_r(morale_day_by_b[d].avg_morale) if d in morale_day_by_b else None for d in range(n_days)]
        morale_day_n   = [morale_day_by_b[d].games_sampled if d in morale_day_by_b else None for d in range(n_days)]

        countries.append({
            "nation_name": c.nation_name,
            "games_played": c.games_played,
            "pct_avg": pct_avg,
            "pct_n": pct_n,
            "pct_vp_avg": pct_vp_avg,
            "day_avg": day_avg,
            "day_n": day_n,
            "day_vp_avg": day_vp_avg,
            "prod_pct": prod_pct,
            "prod_day": prod_day,
            "bld_pct": bld_pct,
            "bld_type_pct": bld_type_pct,
            "morale_pct_avg": morale_pct_avg,
            "morale_pct_n":   morale_pct_n,
            "morale_day_avg": morale_day_avg,
            "morale_day_n":   morale_day_n,
        })
    return {
        "pct_buckets": ts.pct_buckets,
        "max_game_days": ts.max_game_days,
        "generated_at": ts.generated_at.isoformat(),
        "pct_alive":         [_r(p.avg_alive)         for p in ts.player_activity_pct],
        "pct_active_human":  [_r(p.avg_active_human)  for p in ts.player_activity_pct],
        "pct_passive_human": [_r(p.avg_passive_human) for p in ts.player_activity_pct],
        "pct_ai":            [_r(p.avg_ai)            for p in ts.player_activity_pct],
        "pct_alive_n":       [p.games_sampled          for p in ts.player_activity_pct],
        "day_alive":         [_r(p.avg_alive)         for p in ts.player_activity_days],
        "day_active_human":  [_r(p.avg_active_human)  for p in ts.player_activity_days],
        "day_passive_human": [_r(p.avg_passive_human) for p in ts.player_activity_days],
        "day_ai":            [_r(p.avg_ai)            for p in ts.player_activity_days],
        "day_alive_n":       [p.games_sampled          for p in ts.player_activity_days],
        "countries": countries,
    }


def _buildings_columnar(buildings: list[BuildingAggregate]) -> dict:
    cols = [
        "upgrade_identifier", "games_appeared",
        "avg_per_game", "avg_level", "avg_per_tier",
    ]
    rows = [
        [
            b.upgrade_identifier, b.games_appeared,
            _r(b.avg_per_game), _r(b.avg_level),
            {str(tier): _r(avg) for tier, avg in sorted(b.avg_per_tier.items())},
        ]
        for b in buildings
    ]
    return {"columns": cols, "rows": rows}


def write_output(
    output_dir: Path,
    global_agg: GlobalAggregate,
    country_aggs: list[CountryAggregate],
    province_aggs: list[ProvinceAggregate],
    timeseries_agg: TimeSeriesOutput,
    building_aggs: list[BuildingAggregate],
    games: list[GameData],
    replay_dir: Path,
    failed_replays: int,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    start_times = [g.start_time for g in games]
    meta = MetaInfo(
        game_count=len(games),
        failed_replays=failed_replays,
        generated_at=datetime.utcnow(),
        replay_dir=str(replay_dir),
        date_range_start=min(start_times) if start_times else None,
        date_range_end=max(start_times) if start_times else None,
    )

    # Large files: compact columnar format, no indentation
    _write_compact(output_dir / "provinces.json",  _provinces_columnar(province_aggs))
    _write_compact(output_dir / "countries.json",  _countries_columnar(country_aggs))
    _write_compact(output_dir / "timeseries.json", _timeseries_compact(timeseries_agg))
    _write_compact(output_dir / "buildings.json",  _buildings_columnar(building_aggs))

    # Small files: readable indented JSON
    _write_json(output_dir / "global.json", global_agg.model_dump())
    _write_json(output_dir / "meta.json", meta.model_dump())


def _write_compact(path: Path, data) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, separators=(",", ":"), default=_default)


def _write_json(path: Path, data) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, default=_default)
