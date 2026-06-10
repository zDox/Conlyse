"""Section 2.1 — global metrics aggregated across all games."""
import statistics

from .base import BaseAggregator
from ..models.aggregates import DurationBucket, GlobalAggregate
from ..models.intermediate import GameData

_BUCKET_COUNT = 12


class GlobalAggregator(BaseAggregator[GlobalAggregate]):
    def aggregate(self, games: list[GameData]) -> GlobalAggregate:
        if not games:
            return GlobalAggregate(
                total_games=0,
                avg_duration_hours=0,
                median_duration_hours=0,
                std_duration_hours=0,
                duration_distribution=[],
                victory_type_distribution={},
                avg_players_per_game=0,
                avg_human_players_per_game=0,
                player_count_distribution={},
                avg_dropout_rate=0,
                avg_game_days=0,
                avg_update_interval_seconds=0,
            )

        durations = [
            (g.end_time - g.start_time).total_seconds() / 3600.0 for g in games
        ]

        victory_dist: dict[str, int] = {}
        for g in games:
            victory_dist[g.victory_type] = victory_dist.get(g.victory_type, 0) + 1

        human_counts = [
            sum(1 for p in g.players if not p.is_ai) for g in games
        ]
        total_counts = [len(g.players) for g in games]

        # Distribution keyed by human player count (more meaningful for the UI)
        human_count_dist: dict[str, int] = {}
        for c in human_counts:
            human_count_dist[str(c)] = human_count_dist.get(str(c), 0) + 1

        dropout_rates = []
        for g in games:
            human = [p for p in g.players if not p.is_ai]
            if human:
                defeated = sum(1 for p in human if p.is_defeated)
                dropout_rates.append(defeated / len(human))

        # Use actual game_days when available (> 1), otherwise estimate from duration (day ≈ 4h real time)
        game_days_list = []
        for g in games:
            if g.game_days > 1:
                game_days_list.append(float(g.game_days))
            else:
                hours = (g.end_time - g.start_time).total_seconds() / 3600.0
                game_days_list.append(hours / 4.0)

        distribution = _build_histogram(game_days_list, _BUCKET_COUNT)

        update_intervals = [g.avg_update_interval_seconds for g in games if g.avg_update_interval_seconds > 0]

        def _mean(lst: list) -> float:
            return statistics.mean(lst) if lst else 0.0

        all_res = {k for g in games for k in g.game_total_production}
        avg_game_total_production = {
            rtype: _mean([g.game_total_production.get(rtype, 0.0) for g in games])
            for rtype in sorted(all_res)
        }

        # Coalition size distribution (1 = solo, N = coalition of N players)
        coalition_size_dist: dict[str, int] = {}
        coalition_sizes: list[int] = []
        for g in games:
            size = len(g.winner_ids) if g.winner_ids else 1
            coalition_size_dist[str(size)] = coalition_size_dist.get(str(size), 0) + 1
            coalition_sizes.append(size)

        # Top nation-pair co-occurrences in winning coalitions
        from collections import defaultdict as _dd, Counter as _Counter
        pair_counts: dict[tuple[str, str], int] = _dd(int)
        for g in games:
            if g.victory_type != "coalition" or len(g.winner_ids) < 2:
                continue
            id_to_nation = {p.player_id: p.nation_name for p in g.players}
            winner_nations = [id_to_nation[wid] for wid in g.winner_ids if wid in id_to_nation]
            for i in range(len(winner_nations)):
                for j in range(i + 1, len(winner_nations)):
                    a, b = sorted([winner_nations[i], winner_nations[j]])
                    pair_counts[(a, b)] += 1
        top_pairs = sorted(pair_counts.items(), key=lambda x: x[1], reverse=True)[:20]
        top_coalition_pairs = [[a, b, cnt] for (a, b), cnt in top_pairs]

        # Elimination timing distribution — 10% game buckets, human players only
        elim_dist: dict[str, int] = {}
        for g in games:
            for p in g.players:
                if p.is_ai or not p.is_defeated or p.elimination_game_pct is None:
                    continue
                bucket = str(int(p.elimination_game_pct // 10) * 10)
                elim_dist[bucket] = elim_dist.get(bucket, 0) + 1

        return GlobalAggregate(
            total_games=len(games),
            avg_duration_hours=statistics.mean(durations),
            median_duration_hours=statistics.median(durations),
            std_duration_hours=statistics.stdev(durations) if len(durations) > 1 else 0.0,
            duration_distribution=distribution,
            victory_type_distribution=victory_dist,
            avg_players_per_game=statistics.mean(human_counts),
            avg_human_players_per_game=statistics.mean(human_counts),
            player_count_distribution=human_count_dist,
            avg_dropout_rate=statistics.mean(dropout_rates) if dropout_rates else 0.0,
            avg_game_days=statistics.mean(game_days_list) if game_days_list else 0.0,
            avg_update_interval_seconds=statistics.mean(update_intervals) if update_intervals else 0.0,
            avg_wars_per_game=_mean([g.total_wars_declared for g in games]),
            avg_peace_treaties_per_game=_mean([g.total_peace_treaties for g in games]),
            avg_alliances_per_game=_mean([g.total_alliances_formed for g in games]),
            avg_right_of_ways_per_game=_mean([g.total_right_of_ways for g in games]),
            avg_shared_intelligence_per_game=_mean([g.total_shared_intelligence for g in games]),
            avg_game_total_production=avg_game_total_production,
            coalition_size_distribution=coalition_size_dist,
            avg_coalition_size=statistics.mean(coalition_sizes) if coalition_sizes else 0.0,
            top_coalition_pairs=top_coalition_pairs,
            elimination_timing_distribution=elim_dist,
        )


def _build_histogram(values: list[float], n_buckets: int) -> list[DurationBucket]:
    if not values:
        return []
    lo = min(values)
    hi = max(values)
    if hi == lo:
        return [DurationBucket(min_days=lo, max_days=hi, count=len(values))]
    width = (hi - lo) / n_buckets
    buckets: list[DurationBucket] = []
    for i in range(n_buckets):
        b_lo = lo + i * width
        b_hi = lo + (i + 1) * width
        # Last bucket is closed on both ends
        if i < n_buckets - 1:
            count = sum(1 for v in values if b_lo <= v < b_hi)
        else:
            count = sum(1 for v in values if b_lo <= v <= b_hi)
        buckets.append(DurationBucket(min_days=round(b_lo, 1), max_days=round(b_hi, 1), count=count))
    return buckets
