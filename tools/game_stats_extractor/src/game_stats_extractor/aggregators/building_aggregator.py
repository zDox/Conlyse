"""Global building aggregate — frequency, win correlation, and average level per building type."""
import statistics
from collections import defaultdict

from .base import BaseAggregator
from ..models.aggregates import BuildingAggregate
from ..models.intermediate import GameData


class BuildingAggregator(BaseAggregator[list[BuildingAggregate]]):
    def aggregate(self, games: list[GameData]) -> list[BuildingAggregate]:
        uid_game_totals: dict[str, list[float]] = defaultdict(list)
        uid_levels: dict[str, list[float]] = defaultdict(list)
        uid_games_appeared: dict[str, int] = defaultdict(int)
        # uid → tier → list of per-game totals across all players
        uid_tier_totals: dict[str, dict[int, list[float]]] = defaultdict(lambda: defaultdict(list))

        for game in games:
            game_uid_total: dict[str, float] = defaultdict(float)
            game_uid_tier_total: dict[str, dict[int, float]] = defaultdict(lambda: defaultdict(float))

            for player in game.players:
                for uid, cnt in player.final_building_counts.items():
                    game_uid_total[uid] += cnt
                for uid, level in player.final_building_levels.items():
                    uid_levels[uid].append(level)
                for uid, tier_counts in player.final_building_tier_counts.items():
                    for tier, cnt in tier_counts.items():
                        game_uid_tier_total[uid][tier] += cnt

            for uid, total in game_uid_total.items():
                if total > 0:
                    uid_game_totals[uid].append(total)
                    uid_games_appeared[uid] += 1
            for uid, tier_map in game_uid_tier_total.items():
                for tier, total in tier_map.items():
                    uid_tier_totals[uid][tier].append(total)

        result: list[BuildingAggregate] = []
        all_uids = set(uid_game_totals)
        for uid in sorted(all_uids):
            totals = uid_game_totals[uid]
            levels = uid_levels.get(uid, [])
            avg_per_tier = {
                tier: round(statistics.mean(vals), 2)
                for tier, vals in uid_tier_totals.get(uid, {}).items()
            }
            result.append(BuildingAggregate(
                upgrade_identifier=uid,
                games_appeared=uid_games_appeared[uid],
                avg_per_game=round(statistics.mean(totals), 2) if totals else 0.0,
                avg_level=round(statistics.mean(levels), 2) if levels else 0.0,
                avg_per_tier=avg_per_tier,
            ))

        result.sort(key=lambda b: b.avg_per_game, reverse=True)
        return result
