"""Section 2.2 — per-country aggregate across all games where that country was played."""
import statistics
from collections import defaultdict

from .base import BaseAggregator
from ..models.aggregates import CountryAggregate
from ..models.intermediate import GameData, PlayerData


class CountryAggregator(BaseAggregator[list[CountryAggregate]]):
    def aggregate(self, games: list[GameData]) -> list[CountryAggregate]:
        # Group player records by nation_name
        by_nation: dict[str, list[tuple[GameData, PlayerData]]] = defaultdict(list)
        for game in games:
            for player in game.players:
                by_nation[player.nation_name].append((game, player))

        result: list[CountryAggregate] = []
        for nation_name, entries in by_nation.items():
            agg = _aggregate_country(nation_name, entries)
            result.append(agg)

        result.sort(key=lambda c: c.games_played, reverse=True)
        return result


def _aggregate_country(
    nation_name: str, entries: list[tuple[GameData, PlayerData]]
) -> CountryAggregate:
    games_played = len(entries)

    wins = sum(
        1 for game, player in entries if player.player_id in game.winner_ids
    )
    solo_wins = sum(
        1 for game, player in entries
        if player.player_id in game.winner_ids and game.victory_type == "solo"
    )
    coalition_wins = sum(
        1 for game, player in entries
        if player.player_id in game.winner_ids and game.victory_type == "coalition"
    )

    coalition_win_rate = coalition_wins / wins if wins > 0 else 0.0

    winning_coalition_sizes = [
        len(game.winner_ids)
        for game, player in entries
        if player.player_id in game.winner_ids and game.victory_type == "coalition"
    ]

    final_vps = [p.final_vp for _, p in entries]
    final_provs = [p.final_province_count for _, p in entries]
    initial_provs = [p.initial_province_count for _, p in entries]
    expansions = [p.final_province_count - p.initial_province_count for _, p in entries]
    eliminated = sum(1 for _, p in entries if p.is_defeated)
    captures = [p.provinces_captured for _, p in entries]
    losses = [p.provinces_lost for _, p in entries]
    wars_declared = [p.wars_declared for _, p in entries]
    peace_treaties = [p.peace_treaties_signed for _, p in entries]
    alliances_formed = [p.alliances_formed for _, p in entries]
    right_of_ways = [p.right_of_ways_signed for _, p in entries]
    shared_intelligence = [p.shared_intelligence_signed for _, p in entries]

    # Placement: rank by final_vp within each game (1 = best)
    placements: list[float] = []
    for game, player in entries:
        sorted_vps = sorted(
            (p.final_vp for p in game.players), reverse=True
        )
        rank = sorted_vps.index(player.final_vp) + 1 if player.final_vp in sorted_vps else len(sorted_vps)
        placements.append(float(rank))
    median_placement = statistics.median(placements) if placements else 0.0

    # Survival days: game_days for non-eliminated, partial for eliminated
    survival_days = []
    for game, player in entries:
        if not player.is_defeated:
            survival_days.append(float(game.game_days))
        else:
            # Approximation: proportional to final_province_count / initial, capped at game_days
            if game.game_days > 0 and player.initial_province_count > 0:
                fraction = min(1.0, player.final_province_count / player.initial_province_count)
                survival_days.append(game.game_days * fraction)
            else:
                survival_days.append(0.0)

    def _mean(lst: list) -> float:
        return statistics.mean(lst) if lst else 0.0

    all_res = {k for _, p in entries for k in p.avg_production_by_type}
    avg_total_production = {
        rtype: _mean([p.total_production_by_type.get(rtype, 0.0) for _, p in entries])
        for rtype in sorted(all_res)
    }
    avg_production_rate = {
        rtype: _mean([p.avg_production_by_type.get(rtype, 0.0) for _, p in entries])
        for rtype in sorted(all_res)
    }

    all_bld = {uid for _, p in entries for uid in p.final_building_counts}
    avg_final_building_counts = {
        uid: _mean([p.final_building_counts.get(uid, 0.0) for _, p in entries])
        for uid in sorted(all_bld)
    }
    all_bld_lvl = {uid for _, p in entries for uid in p.final_building_levels}
    avg_final_building_levels = {
        uid: _mean([p.final_building_levels[uid] for _, p in entries if uid in p.final_building_levels])
        for uid in sorted(all_bld_lvl)
    }

    # Human-only entries (native_computer=False) for metrics that should exclude AI-controlled slots
    human_entries = [(g, p) for g, p in entries if not p.is_native_computer]
    human_n = len(human_entries)

    human_eliminated = sum(1 for _, p in human_entries if p.is_defeated)
    human_elimination_rate = human_eliminated / human_n if human_n > 0 else 0.0

    morale_vals = [p.avg_national_morale for _, p in human_entries if p.avg_national_morale > 0]
    avg_national_morale = _mean(morale_vals)

    elim_pcts = [p.elimination_game_pct for _, p in human_entries if p.elimination_game_pct is not None]
    avg_elimination_pct: float | None = _mean(elim_pcts) if elim_pcts else None

    return CountryAggregate(
        nation_name=nation_name,
        games_played=games_played,
        wins=wins,
        win_rate=wins / games_played,
        avg_final_vp=_mean(final_vps),
        avg_placement=_mean(placements),
        median_placement=median_placement,
        avg_final_provinces=_mean(final_provs),
        avg_initial_provinces=_mean(initial_provs),
        avg_expansion=_mean(expansions),
        avg_provinces_captured=_mean(captures),
        avg_provinces_lost=_mean(losses),
        elimination_rate=human_elimination_rate,
        avg_survival_days=_mean(survival_days),
        avg_wars_declared=_mean(wars_declared),
        avg_peace_treaties_signed=_mean(peace_treaties),
        avg_alliances_formed=_mean(alliances_formed),
        avg_right_of_ways_signed=_mean(right_of_ways),
        avg_shared_intelligence_signed=_mean(shared_intelligence),
        avg_total_production=avg_total_production,
        avg_production_rate=avg_production_rate,
        avg_final_building_counts=avg_final_building_counts,
        avg_final_building_levels=avg_final_building_levels,
        avg_national_morale=avg_national_morale,
        solo_wins=solo_wins,
        coalition_wins=coalition_wins,
        coalition_win_rate=coalition_win_rate,
        avg_winning_coalition_size=_mean(winning_coalition_sizes),
        avg_elimination_pct=avg_elimination_pct,
    )
