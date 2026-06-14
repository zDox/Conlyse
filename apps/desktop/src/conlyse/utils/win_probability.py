"""
Build live win-probability feature snapshots from the current replay tick.

The dict schema and units produced here MUST match
`game_stats_extractor.models.training.TrainingRow.to_dict()` (the schema the
win-probability model was trained on) — see `training_rows_from_game_data()`
and `ReplayExtractor._extract()` for the source-of-truth field semantics.
Any drift here causes silent train/serve skew.
"""
from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING

from conflict_interface.data_types.newest.foreign_affairs_state.foreign_affairs_state_enums import (
    ForeignAffairRelationTypes,
)

if TYPE_CHECKING:
    from conflict_interface.interface.replay_interface import ReplayInterface

RESOURCE_TYPES = ["MONEY", "SUPPLY", "FUEL", "COMPONENT", "ELECTRONIC", "RARE_MATERIAL"]

# Live game-state enums may come from a versioned module (data_types.vXXX) while
# this module imports from data_types.newest — different classes, so compare .value.
#
# Only WAR / RIGHT_OF_WAY / SHARED_INTELLIGENCE are tracked: a sample of real games
# showed MUTUAL_PROTECTION / NON_AGGRESSION_PACT / CEASEFIRE never occur in practice.
_WAR_VAL = ForeignAffairRelationTypes.WAR.value
_ROW_VAL = ForeignAffairRelationTypes.RIGHT_OF_WAY.value
_INTEL_VAL = ForeignAffairRelationTypes.SHARED_INTELLIGENCE.value

# Upgrades that have resource costs but aren't persistent buildings (one-time actions).
_NON_BUILDING_NAMES = frozenset({"Annex City", "Relocate Headquarters", "Nationalize"})


def _is_land_province(province) -> bool:
    return hasattr(province, "owner_id") and hasattr(province, "morale")


def _is_player_building(upgrade_type) -> bool:
    if upgrade_type.upgrade_name in _NON_BUILDING_NAMES:
        return False
    return bool(upgrade_type.costs)


def _is_built(upgrade, upgrade_type) -> bool:
    condition = upgrade.condition
    if condition is None or condition <= 0:
        return False
    return condition >= upgrade_type.build_condition


def _building_type_key(upgrade_type) -> tuple[str, int]:
    identifier = upgrade_type.upgrade_identifier or upgrade_type.upgrade_name or str(upgrade_type.id)
    return identifier, upgrade_type.tier


def _building_column(identifier: str) -> str:
    return "bld_" + identifier.replace(" ", "_").replace("-", "_")


def _relation_counts(neighbor_relations: dict, player_id: int) -> tuple[int, int, int]:
    """
    Count `player_id`'s *current* outgoing relations by type (sender perspective),
    matching `TrainingRow`/`training_rows_from_game_data` semantics. `neighbor_relations`
    is keyed by 0-indexed player id, so subtract 1 from the 1-indexed `player_id`.
    """
    row = neighbor_relations.get(player_id - 1, {})
    war_n = row_n = intel_n = 0
    for rel in row.values():
        val = rel.value if rel is not None else None
        if val == _WAR_VAL:
            war_n += 1
        elif val == _ROW_VAL:
            row_n += 1
        elif val == _INTEL_VAL:
            intel_n += 1
    return war_n, row_n, intel_n


def _pct_game(ritf: "ReplayInterface") -> int:
    total = (ritf.last_time - ritf.start_time).total_seconds()
    if total <= 0:
        return 0
    elapsed = (ritf.current_time - ritf.start_time).total_seconds()
    return max(0, min(100, round((elapsed / total) * 100 / 5) * 5))


def build_snapshots(ritf: "ReplayInterface") -> list[dict]:
    """
    Build one feature dict per player who currently owns territory, matching
    `TrainingRow.to_dict()`. Suitable for `ml.predict.Predictor.predict()`.
    """
    game_state = ritf.game_state
    if game_state is None:
        return []

    upgrade_types = dict(game_state.states.mod_state.upgrades)
    players = ritf.get_players()

    province_count: dict[int, int] = defaultdict(int)
    morale_sum: dict[int, float] = defaultdict(float)
    production: dict[int, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    building_counts: dict[int, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    building_type_counts: dict[int, dict[tuple[str, int], float]] = defaultdict(lambda: defaultdict(float))

    for province in game_state.states.map_state.map.provinces.values():
        if not _is_land_province(province):
            continue
        owner_id = province.owner_id
        if owner_id not in players:
            continue

        province_count[owner_id] += 1
        morale_sum[owner_id] += float(province.morale)
        production[owner_id]["MONEY"] += float(int(province.money_production or 0))

        rtype = province.resource_production_type
        rtype_name = rtype.name if rtype and hasattr(rtype, "name") else None
        if rtype_name and rtype_name in RESOURCE_TYPES:
            production[owner_id][rtype_name] += float(int(province.resource_production or 0))

        for upgrade in province.upgrades_set or []:
            upgrade_type = upgrade_types.get(upgrade.id)
            if upgrade_type is None:
                continue
            if not _is_player_building(upgrade_type) or not _is_built(upgrade, upgrade_type):
                continue
            identifier, tier = _building_type_key(upgrade_type)
            building_counts[owner_id][identifier] += 1
            building_type_counts[owner_id][(identifier, tier)] += 1

    pct_game = _pct_game(ritf)
    total_players = len(players)

    foreign_affairs_state = game_state.states.foreign_affairs_state
    neighbor_relations = (
        foreign_affairs_state.relations.neighbor_relations
        if foreign_affairs_state and foreign_affairs_state.relations
        else {}
    )

    snapshots: list[dict] = []
    for player_id, profile in players.items():
        count = province_count.get(player_id, 0)
        if count == 0:
            continue  # defeated / no territory — no meaningful win-probability signal

        at_war_count, right_of_way_count, shared_intelligence_count = _relation_counts(
            neighbor_relations, player_id
        )

        row = {
            "game_id": ritf.game_id or 0,
            "player_id": player_id,
            "nation_name": profile.nation_name,
            "pct_game": pct_game,
            "bucket_coverage": 1,
            "province_count": count,
            "vp": int(profile.victory_points),
            "national_morale": morale_sum[player_id] / count,
            "at_war_count": at_war_count,
            "right_of_way_count": right_of_way_count,
            "shared_intelligence_count": shared_intelligence_count,
            "is_ai": int(profile.computer_player),
            "total_players": total_players,
        }
        for rtype in RESOURCE_TYPES:
            row[f"{rtype.lower()}_production"] = production[player_id].get(rtype, 0.0)
        for identifier, count_ in building_counts[player_id].items():
            row[_building_column(identifier)] = count_
        for (identifier, tier), count_ in building_type_counts[player_id].items():
            row[f"{_building_column(identifier)}_t{tier}"] = count_

        snapshots.append(row)

    return snapshots
