"""Section 1.4 — per-country province-count and production time series, averaged across all games."""
import statistics
from collections import defaultdict
from datetime import datetime

from .base import BaseAggregator
from ..models.aggregates import BuildingTimeSeriesPoint, CountryTimeSeries, MoraleTimeSeriesPoint, PlayerActivityPoint, ProductionTimeSeriesPoint, TimeSeriesOutput, TimeSeriesPoint
from ..models.intermediate import GameData, PlayerData

_PCT_BUCKETS = list(range(0, 101, 5))


class TimeSeriesAggregator(BaseAggregator[TimeSeriesOutput]):
    def __init__(self, min_games: int = 3):
        self._min_games = min_games

    def aggregate(self, games: list[GameData]) -> TimeSeriesOutput:
        by_nation: dict[str, list[tuple[GameData, PlayerData]]] = defaultdict(list)
        for game in games:
            for player in game.players:
                by_nation[player.nation_name].append((game, player))

        countries: list[CountryTimeSeries] = []
        max_game_days = 0

        for nation_name, entries in by_nation.items():
            if len(entries) < self._min_games:
                continue

            pct_series = _aggregate_buckets(
                [p.pct_buckets for _, p in entries],
                [p.pct_vp_buckets for _, p in entries],
                _PCT_BUCKETS,
            )

            all_day_keys: set[int] = set()
            for _, p in entries:
                all_day_keys.update(p.day_buckets.keys())
            day_series = _aggregate_buckets(
                [p.day_buckets for _, p in entries],
                [p.day_vp_buckets for _, p in entries],
                sorted(all_day_keys),
            )

            if all_day_keys:
                max_game_days = max(max_game_days, max(all_day_keys))

            all_res_types = {rtype for _, p in entries for rtype in p.production_pct_buckets}
            all_res_day_keys: set[int] = set()
            for _, p in entries:
                for buckets in p.production_day_buckets.values():
                    all_res_day_keys.update(buckets.keys())

            production_pct_game = {
                rtype: _aggregate_prod_buckets(
                    [p.production_pct_buckets.get(rtype, {}) for _, p in entries], _PCT_BUCKETS
                )
                for rtype in sorted(all_res_types)
            }
            production_game_days = {
                rtype: _aggregate_prod_buckets(
                    [p.production_day_buckets.get(rtype, {}) for _, p in entries],
                    sorted(all_res_day_keys),
                )
                for rtype in sorted(all_res_types)
            }

            all_bld_types = {uid for _, p in entries for uid in p.building_pct_buckets}
            building_pct_game = {
                uid: _aggregate_building_buckets(
                    [p.building_pct_buckets.get(uid, {}) for _, p in entries], _PCT_BUCKETS
                )
                for uid in sorted(all_bld_types)
            }

            all_bld_type_keys = {key for _, p in entries for key in p.building_type_pct_buckets}
            building_type_pct_game: dict[str, dict[int, list[BuildingTimeSeriesPoint]]] = defaultdict(dict)
            for uid, tier in sorted(all_bld_type_keys):
                building_type_pct_game[uid][tier] = _aggregate_building_buckets(
                    [p.building_type_pct_buckets.get((uid, tier), {}) for _, p in entries], _PCT_BUCKETS
                )
            building_type_pct_game = dict(building_type_pct_game)

            morale_pct_game = _aggregate_morale_buckets(
                [p.morale_pct_buckets for _, p in entries], _PCT_BUCKETS
            )
            all_morale_day_keys: set[int] = set()
            for _, p in entries:
                all_morale_day_keys.update(p.morale_day_buckets.keys())
            morale_game_days = _aggregate_morale_buckets(
                [p.morale_day_buckets for _, p in entries], sorted(all_morale_day_keys)
            )

            countries.append(CountryTimeSeries(
                nation_name=nation_name,
                games_played=len(entries),
                pct_game=pct_series,
                game_days=day_series,
                production_pct_game=production_pct_game,
                production_game_days=production_game_days,
                building_pct_game=building_pct_game,
                building_type_pct_game=building_type_pct_game,
                morale_pct_game=morale_pct_game,
                morale_game_days=morale_game_days,
            ))

        countries.sort(key=lambda c: c.games_played, reverse=True)

        player_activity_pct = _aggregate_player_activity(games, _PCT_BUCKETS, mode="pct")
        player_activity_days = _aggregate_player_activity(
            games, list(range(max_game_days + 1)), mode="days"
        )

        return TimeSeriesOutput(
            countries=countries,
            pct_buckets=_PCT_BUCKETS,
            max_game_days=max_game_days,
            generated_at=datetime.utcnow(),
            player_activity_pct=player_activity_pct,
            player_activity_days=player_activity_days,
        )


def _aggregate_player_activity(
    games: list[GameData],
    bucket_keys: list[int],
    mode: str,
) -> list[PlayerActivityPoint]:
    points: list[PlayerActivityPoint] = []
    for b in bucket_keys:
        alive_vals: list[float] = []
        active_human_vals: list[float] = []
        passive_human_vals: list[float] = []
        ai_vals: list[float] = []
        if mode == "pct":
            for g in games:
                if b in g.pct_alive_buckets:
                    alive_vals.append(g.pct_alive_buckets[b])
                    active_human_vals.append(g.pct_active_human_buckets.get(b, 0))
                    passive_human_vals.append(g.pct_passive_human_buckets.get(b, 0))
                    ai_vals.append(g.pct_ai_buckets.get(b, 0))
        else:
            for g in games:
                if b in g.day_alive_buckets:
                    alive_vals.append(g.day_alive_buckets[b])
                    active_human_vals.append(g.day_active_human_buckets.get(b, 0))
                    passive_human_vals.append(g.day_passive_human_buckets.get(b, 0))
                    ai_vals.append(g.day_ai_buckets.get(b, 0))
        if not alive_vals:
            continue
        points.append(PlayerActivityPoint(
            bucket=b,
            avg_alive=round(statistics.mean(alive_vals), 2),
            avg_active_human=round(statistics.mean(active_human_vals), 2),
            avg_passive_human=round(statistics.mean(passive_human_vals), 2),
            avg_ai=round(statistics.mean(ai_vals), 2),
            games_sampled=len(alive_vals),
        ))
    return points


def _aggregate_buckets(
    prov_buckets: list[dict[int, int]],
    vp_buckets: list[dict[int, int]],
    bucket_keys: list[int],
) -> list[TimeSeriesPoint]:
    points: list[TimeSeriesPoint] = []
    for b in bucket_keys:
        prov_values = [pb[b] for pb in prov_buckets if b in pb]
        vp_values = [vb[b] for vb in vp_buckets if b in vb]
        if not prov_values:
            continue
        points.append(TimeSeriesPoint(
            bucket=b,
            avg_provinces=round(statistics.mean(prov_values), 2),
            avg_vp=round(statistics.mean(vp_values), 2) if vp_values else 0.0,
            games_sampled=len(prov_values),
        ))
    return points


def _aggregate_prod_buckets(
    player_buckets: list[dict[int, float]],
    bucket_keys: list[int],
) -> list[ProductionTimeSeriesPoint]:
    points: list[ProductionTimeSeriesPoint] = []
    for b in bucket_keys:
        values = [pb[b] for pb in player_buckets if b in pb]
        if not values:
            continue
        points.append(ProductionTimeSeriesPoint(
            bucket=b,
            avg_production=round(statistics.mean(values), 2),
            games_sampled=len(values),
        ))
    return points


def _aggregate_building_buckets(
    player_buckets: list[dict[int, float]],
    bucket_keys: list[int],
) -> list[BuildingTimeSeriesPoint]:
    points: list[BuildingTimeSeriesPoint] = []
    for b in bucket_keys:
        values = [pb[b] for pb in player_buckets if b in pb]
        if not values:
            continue
        points.append(BuildingTimeSeriesPoint(
            bucket=b,
            avg_count=round(statistics.mean(values), 2),
            games_sampled=len(values),
        ))
    return points


def _aggregate_morale_buckets(
    player_buckets: list[dict[int, float]],
    bucket_keys: list[int],
) -> list[MoraleTimeSeriesPoint]:
    points: list[MoraleTimeSeriesPoint] = []
    for b in bucket_keys:
        values = [pb[b] for pb in player_buckets if b in pb]
        if not values:
            continue
        points.append(MoraleTimeSeriesPoint(
            bucket=b,
            avg_morale=round(statistics.mean(values), 2),
            games_sampled=len(values),
        ))
    return points
