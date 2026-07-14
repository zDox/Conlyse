"""Section 2.3 — per-province aggregate across all games where that province appeared."""
import statistics
from collections import defaultdict

from .base import BaseAggregator
from ..models.aggregates import ProvinceAggregate
from ..models.intermediate import GameData, ProvinceData


class ProvinceAggregator(BaseAggregator[list[ProvinceAggregate]]):
    def __init__(self, min_appearances: int = 3):
        # Only aggregate provinces that appear in at least this many games
        self._min_appearances = min_appearances

    def aggregate(self, games: list[GameData]) -> list[ProvinceAggregate]:
        # Group province records by province_id
        by_province: dict[int, list[tuple[GameData, ProvinceData]]] = defaultdict(list)
        for game in games:
            for province in game.provinces:
                by_province[province.province_id].append((game, province))

        result: list[ProvinceAggregate] = []
        for province_id, entries in by_province.items():
            if len(entries) < self._min_appearances:
                continue
            agg = _aggregate_province(province_id, entries)
            result.append(agg)

        result.sort(key=lambda p: p.games_appeared, reverse=True)
        return result


def _aggregate_province(
    province_id: int, entries: list[tuple[GameData, ProvinceData]]
) -> ProvinceAggregate:
    games_appeared = len(entries)

    # Use the most common name (names can vary slightly across replays)
    name_counts: dict[str, int] = defaultdict(int)
    for _, p in entries:
        name_counts[p.province_name] += 1
    province_name = max(name_counts, key=lambda k: name_counts[k])

    terrain_types: dict[str, int] = defaultdict(int)
    for _, p in entries:
        terrain_types[p.terrain_type] += 1
    terrain_type = max(terrain_types, key=lambda k: terrain_types[k])

    is_coastal = sum(1 for _, p in entries if p.is_coastal) > games_appeared / 2

    region_counts: dict[str, int] = defaultdict(int)
    for _, p in entries:
        region_counts[p.region] += 1
    region = max(region_counts, key=lambda k: region_counts[k])

    # Original (legal/home) owner nation — resolve each game's legal_owner_id
    # (a per-game player slot) to that game's nation name, then take the mode.
    owner_nation_counts: dict[str, int] = defaultdict(int)
    for game, p in entries:
        if p.legal_owner_id < 0:
            continue
        for player in game.players:
            if player.player_id == p.legal_owner_id:
                owner_nation_counts[player.nation_name] += 1
                break
    original_owner_nation = (
        max(owner_nation_counts, key=lambda k: owner_nation_counts[k]) if owner_nation_counts else None
    )

    ownership_changes = [p.ownership_changes for _, p in entries]
    avg_ownership_changes = statistics.mean(ownership_changes)
    contest_frequency = sum(1 for c in ownership_changes if c > 0) / games_appeared

    # Win correlation: fraction of games where the winner owned this province at game end
    winner_owned = sum(
        1
        for game, province in entries
        if province.final_owner_id in game.winner_ids
    )
    win_correlation = winner_owned / games_appeared

    # Resource production — use the most common non-None type
    res_types = [p.resource_production_type for _, p in entries if p.resource_production_type]
    resource_production_type: str | None = None
    if res_types:
        type_counts: dict[str, int] = defaultdict(int)
        for t in res_types:
            type_counts[t] += 1
        resource_production_type = max(type_counts, key=lambda k: type_counts[k])

    avg_resource_production = statistics.mean(p.resource_production for _, p in entries)
    avg_money_production = statistics.mean(p.money_production for _, p in entries)
    avg_morale = statistics.mean(p.avg_morale for _, p in entries)

    all_uids = {uid for _, p in entries for uid in p.final_upgrade_counts}
    typical_buildings = {
        uid: sum(1 for _, p in entries if p.final_upgrade_counts.get(uid, 0) > 0) / games_appeared
        for uid in sorted(all_uids)
    }
    # Average level is not stored per-province in intermediate data (only per-player), so omit
    avg_building_levels: dict[str, float] = {}

    return ProvinceAggregate(
        province_id=province_id,
        province_name=province_name,
        terrain_type=terrain_type,
        is_coastal=is_coastal,
        region=region,
        original_owner_nation=original_owner_nation,
        games_appeared=games_appeared,
        avg_ownership_changes=avg_ownership_changes,
        contest_frequency=contest_frequency,
        win_correlation=win_correlation,
        resource_production_type=resource_production_type,
        avg_resource_production=avg_resource_production,
        avg_money_production=avg_money_production,
        avg_morale=avg_morale,
        typical_buildings=typical_buildings,
        avg_building_levels=avg_building_levels,
    )
