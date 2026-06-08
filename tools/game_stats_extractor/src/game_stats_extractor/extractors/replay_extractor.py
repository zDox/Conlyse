"""
Extracts per-game statistics from a single .conrp replay file.

Opens the replay once, registers province hooks for owner_id and morale, then
iterates timestamps. Only changed provinces fire events — no full province scan
per tick. Player territory counts are maintained incrementally on ownership events.
"""
import logging
from collections import defaultdict
from pathlib import Path
from typing import Optional

from conflict_interface.data_types.newest.foreign_affairs_state.foreign_affairs_state_enums import (
    ForeignAffairRelationTypes,
)
from conflict_interface.hook_system.replay_hook_tag import ReplayHookTag
from conflict_interface.interface.replay_interface import ReplayInterface

from .base import BaseExtractor
from ..models.intermediate import GameData, PlayerData, ProvinceData

logger = logging.getLogger(__name__)

_UNOWNED = 0

# One-time actions and game-managed upgrades that should not appear in building statistics.
# Programmatic rule: only upgrades with non-empty costs are player-buildable; but these actions
# have costs yet produce no persistent building that we want to count.
_NON_BUILDING_NAMES = frozenset({"Annex City", "Relocate Headquarters", "Nationalize"})


def _is_land_province(province) -> bool:
    """True for LandProvince objects (which have owner_id / morale)."""
    return hasattr(province, "owner_id") and hasattr(province, "morale")


def _upgrade_identifier(upgrade_id: int, ut_map: dict) -> str:
    ut = ut_map.get(upgrade_id)
    if ut is None:
        return str(upgrade_id)
    return ut.upgrade_identifier or ut.upgrade_name or str(upgrade_id)


def _upgrade_type_key(upgrade_id: int, ut_map: dict) -> tuple[str, int]:
    """Building type key — (Building Group identifier, Tier within that group)."""
    ut = ut_map.get(upgrade_id)
    if ut is None:
        return (str(upgrade_id), 0)
    return (ut.upgrade_identifier or ut.upgrade_name or str(upgrade_id), ut.tier)


def _is_player_building(upgrade_id: int, ut_map: dict) -> bool:
    """True only for player-constructable persistent buildings (have resource costs, not one-time actions)."""
    ut = ut_map.get(upgrade_id)
    if ut is None:
        return False
    if ut.upgrade_name in _NON_BUILDING_NAMES:
        return False
    return bool(ut.costs)


def _is_built(upgrade, ut_map: dict) -> bool:
    """A building is 'built' when its condition meets or exceeds build_condition."""
    cond = upgrade.condition
    if cond is None or cond <= 0:
        return False
    ut = ut_map.get(upgrade.id)
    if ut is None:
        return True
    return cond >= ut.build_condition


def _province_built_buildings(province, ut_map: dict) -> dict[tuple[str, int], int]:
    counts: dict[tuple[str, int], int] = {}
    upgrades = getattr(province, "upgrades", None) or {}
    for upgrade in upgrades.values():
        if _is_player_building(upgrade.id, ut_map) and _is_built(upgrade, ut_map):
            key = _upgrade_type_key(upgrade.id, ut_map)
            counts[key] = counts.get(key, 0) + 1
    return counts


def _pct_bucket(elapsed: float, total: float) -> int:
    if total <= 0:
        return 0
    return max(0, min(100, round((elapsed / total) * 100 / 5) * 5))


def _day_bucket(elapsed: float, total: float, game_days: int) -> int:
    if total <= 0 or game_days <= 0:
        return 0
    return round((elapsed / total) * game_days)


def _finalize_buckets(sums: dict[int, float], ns: dict[int, int]) -> dict[int, int]:
    return {b: round(sums[b] / ns[b]) for b in sums if ns[b] > 0}


def _finalize_float_buckets(sums: dict[int, float], ns: dict[int, int]) -> dict[int, float]:
    return {b: sums[b] / ns[b] for b in sums if ns[b] > 0}


def _group_building_counts(type_counts: dict[tuple[str, int], int]) -> dict[str, int]:
    """Sum (uid, tier)-keyed Building Type counts into uid-keyed Building Group counts."""
    totals: dict[str, int] = defaultdict(int)
    for (uid, _tier), cnt in type_counts.items():
        totals[uid] += cnt
    return dict(totals)


class ReplayExtractor(BaseExtractor):
    def __init__(self, map_data_dir: Optional[Path] = None):
        self._map_data_dir = map_data_dir

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def extract(self, file_path: Path) -> GameData:
        # --- Fast metadata check (no static map data needed) ---
        meta_replay = ReplayInterface(file_path)
        try:
            if not meta_replay.open(mode="read_metadata"):
                raise ValueError("replay.open(read_metadata) returned False")
            meta = meta_replay.get_timeline_metadata()
        finally:
            meta_replay.close()

        if not meta.game_ended:
            raise ValueError("game has not ended yet (game_ended=False in timeline metadata)")

        # --- Full extraction ---
        static_map_data = self._resolve_static_map_data(file_path)
        replay = ReplayInterface(file_path, static_map_data=static_map_data)
        try:
            if not replay.open():
                raise ValueError("replay.open() returned False — file may be incomplete or corrupted")
            return self._extract(replay, file_path, meta)
        finally:
            replay.close()

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _resolve_static_map_data(self, file_path: Path) -> dict[str, Path]:
        if self._map_data_dir is None:
            return {}
        result: dict[str, Path] = {}
        for bin_file in self._map_data_dir.glob("*.bin"):
            result[bin_file.stem] = bin_file
        return result

    def _extract(self, replay: ReplayInterface, file_path: Path, meta) -> GameData:
        start_time = replay.start_time
        end_time = replay.last_time
        timestamps = replay.get_timestamps()
        total_updates = len(timestamps)
        avg_update_interval_seconds = (
            (end_time - start_time).total_seconds() / (total_updates - 1)
            if total_updates > 1
            else 0.0
        )

        # game_id and day_of_game come from the timeline metadata header (authoritative)
        game_id: int = meta.game_id or 0
        if not game_id:
            try:
                game_id = int(file_path.stem.replace("game_", ""))
            except (ValueError, AttributeError):
                pass
        game_days: int = meta.day_of_game or 0

        # ---- Initial state ----
        replay.jump_to(start_time)
        gs = replay.game_state
        if gs is None:
            raise ValueError("game_state is None after jump_to(start_time)")

        map_obj = gs.states.map_state.map
        map_id: str = getattr(map_obj, "map_id", "unknown")

        # Upgrade type registry: id → UpgradeType (name + build_condition metadata)
        ut_map: dict = dict(gs.states.mod_state.upgrades)

        initial_land = {
            pid: p
            for pid, p in map_obj.provinces.items()
            if _is_land_province(p)
        }

        # Province static info (name, terrain, coastal) — read once
        province_meta: dict[int, dict] = {
            pid: {
                "name": p.name,
                "terrain_type": str(p.terrain_type.name) if hasattr(p.terrain_type, "name") else str(p.terrain_type),
                "is_coastal": bool(getattr(p, "costal", False)),
                "resource_production_type": (
                    str(p.resource_production_type.name)
                    if p.resource_production_type and hasattr(p.resource_production_type, "name")
                    else (str(p.resource_production_type) if p.resource_production_type else None)
                ),
            }
            for pid, p in initial_land.items()
        }

        initial_owners: dict[int, int] = {pid: p.owner_id for pid, p in initial_land.items()}

        # Province production state: pid -> {resource_type_name: current_amount}
        # "MONEY" always present; additional type key present if province has resource_production_type
        province_production: dict[int, dict[str, float]] = {}
        for pid, p in initial_land.items():
            prod: dict[str, float] = {"MONEY": float(int(p.money_production or 0))}
            rtype = province_meta[pid]["resource_production_type"]
            if rtype:
                prod[rtype] = float(int(p.resource_production or 0))
            province_production[pid] = prod

        # Per-player running production sums (updated on ownership and upgrade events)
        current_player_production: dict[int, dict[str, float]] = defaultdict(lambda: defaultdict(float))
        for pid, prod in province_production.items():
            owner = initial_owners[pid]
            if owner > _UNOWNED:
                for rtype, amount in prod.items():
                    current_player_production[owner][rtype] += amount

        # Incrementally maintained ownership and player counts
        current_owners: dict[int, int] = dict(initial_owners)
        current_player_counts: dict[int, int] = defaultdict(int)
        for oid in initial_owners.values():
            if oid > _UNOWNED:
                current_player_counts[oid] += 1

        ownership_changes: dict[int, int] = defaultdict(int)
        player_captures: dict[int, int] = defaultdict(int)
        player_losses: dict[int, int] = defaultdict(int)

        # Morale accumulators — seeded with the initial snapshot
        prov_morale_sum: dict[int, float] = {pid: float(p.morale) for pid, p in initial_land.items()}
        prov_morale_n: dict[int, int] = {pid: 1 for pid in initial_land}
        prov_morale_min: dict[int, float] = {pid: float(p.morale) for pid, p in initial_land.items()}
        prov_morale_max: dict[int, float] = {pid: float(p.morale) for pid, p in initial_land.items()}

        # Player territory accumulators — seeded with the initial snapshot
        player_prov_sum: dict[int, float] = defaultdict(float)
        player_prov_n: dict[int, int] = defaultdict(int)
        player_prov_max: dict[int, int] = defaultdict(int)
        player_prov_min: dict[int, int] = {}
        for player_id, cnt in current_player_counts.items():
            if cnt > 0:
                player_prov_sum[player_id] = float(cnt)
                player_prov_n[player_id] = 1
                player_prov_max[player_id] = cnt
                player_prov_min[player_id] = cnt

        # Time-series bucket accumulators
        total_duration_seconds = (end_time - start_time).total_seconds()
        pct_bucket_sum: dict[int, dict[int, float]] = defaultdict(lambda: defaultdict(float))
        pct_bucket_n: dict[int, dict[int, int]] = defaultdict(lambda: defaultdict(int))
        day_bucket_sum: dict[int, dict[int, float]] = defaultdict(lambda: defaultdict(float))
        day_bucket_n: dict[int, dict[int, int]] = defaultdict(lambda: defaultdict(int))
        pct_vp_bucket_sum: dict[int, dict[int, float]] = defaultdict(lambda: defaultdict(float))
        pct_vp_bucket_n: dict[int, dict[int, int]] = defaultdict(lambda: defaultdict(int))
        day_vp_bucket_sum: dict[int, dict[int, float]] = defaultdict(lambda: defaultdict(float))
        day_vp_bucket_n: dict[int, dict[int, int]] = defaultdict(lambda: defaultdict(int))
        # Game-level alive-player bucket accumulators (4 categories)
        pct_alive_sum: dict[int, float] = defaultdict(float)
        pct_alive_n: dict[int, int] = defaultdict(int)
        pct_active_human_sum: dict[int, float] = defaultdict(float)
        pct_active_human_n: dict[int, int] = defaultdict(int)
        pct_passive_human_sum: dict[int, float] = defaultdict(float)
        pct_passive_human_n: dict[int, int] = defaultdict(int)
        pct_ai_sum: dict[int, float] = defaultdict(float)
        pct_ai_n: dict[int, int] = defaultdict(int)
        day_alive_sum: dict[int, float] = defaultdict(float)
        day_alive_n: dict[int, int] = defaultdict(int)
        day_active_human_sum: dict[int, float] = defaultdict(float)
        day_active_human_n: dict[int, int] = defaultdict(int)
        day_passive_human_sum: dict[int, float] = defaultdict(float)
        day_passive_human_n: dict[int, int] = defaultdict(int)
        day_ai_sum: dict[int, float] = defaultdict(float)
        day_ai_n: dict[int, int] = defaultdict(int)

        # Production accumulators: [player_id][resource_type][bucket]
        player_prod_sum: dict[int, dict[str, float]] = defaultdict(lambda: defaultdict(float))
        player_prod_n: dict[int, int] = defaultdict(int)
        player_total_prod: dict[int, dict[str, float]] = defaultdict(lambda: defaultdict(float))
        player_peak_prod: dict[int, dict[str, float]] = defaultdict(lambda: defaultdict(float))
        prod_pct_sum: dict[int, dict[str, dict[int, float]]] = defaultdict(lambda: defaultdict(lambda: defaultdict(float)))
        prod_pct_n:   dict[int, dict[str, dict[int, int]]]   = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
        prod_day_sum: dict[int, dict[str, dict[int, float]]] = defaultdict(lambda: defaultdict(lambda: defaultdict(float)))
        prod_day_n:   dict[int, dict[str, dict[int, int]]]   = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
        prev_time = start_time

        # Building accumulators — keyed by (Building Group identifier, Tier), i.e. "Building Type".
        # Seeded from initial state (one-time scan of ~3400 provinces)
        current_province_buildings: dict[int, dict[tuple[str, int], int]] = {
            pid: _province_built_buildings(p, ut_map) for pid, p in initial_land.items()
        }
        current_player_buildings: dict[int, dict[tuple[str, int], int]] = defaultdict(lambda: defaultdict(int))
        for pid, bld in current_province_buildings.items():
            owner = initial_owners.get(pid, _UNOWNED)
            if owner > _UNOWNED:
                for type_key, cnt in bld.items():
                    current_player_buildings[owner][type_key] += cnt
        # Building Group (uid) time series — derived by summing counts across tiers at snapshot time
        bld_pct_sum: dict[int, dict[str, dict[int, float]]] = defaultdict(lambda: defaultdict(lambda: defaultdict(float)))
        bld_pct_n:   dict[int, dict[str, dict[int, int]]]   = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
        # Building Type ((uid, tier)) time series
        bldtype_pct_sum: dict[int, dict[tuple[str, int], dict[int, float]]] = defaultdict(lambda: defaultdict(lambda: defaultdict(float)))
        bldtype_pct_n:   dict[int, dict[tuple[str, int], dict[int, int]]]   = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
        bld_level_sum: dict[int, dict[str, float]] = defaultdict(lambda: defaultdict(float))
        bld_level_n:   dict[int, dict[str, int]]   = defaultdict(lambda: defaultdict(int))

        # Diplomacy counters — keyed by 1-indexed player id; populated by ForeignAffairsChanged events
        dp_wars: dict[int, int] = defaultdict(int)
        dp_peace: dict[int, int] = defaultdict(int)
        dp_alliances: dict[int, int] = defaultdict(int)
        dp_allianced: dict[int, int] = defaultdict(int)
        dp_rows: dict[int, int] = defaultdict(int)
        game_wars = game_peace = game_alliances = game_allianced = game_rows = 0

        # Current diplomatic state — 0-indexed sender -> receiver -> ForeignAffairRelationTypes.value.
        # Replaced wholesale with the new snapshot on each ForeignAffairsRelationChanged event,
        # then sampled per-tick (alongside province/VP/morale) into pct buckets below.
        #
        # Note: only WAR, RIGHT_OF_WAY and SHARED_INTELLIGENCE were ever observed in real
        # games (sampled ~18 replays) — MUTUAL_PROTECTION/NON_AGGRESSION_PACT/CEASEFIRE/
        # TRADE_EMBARGO never occur, so only the three meaningful types are tracked.
        current_relations: dict[int, dict[int, int]] = {}
        dp_war_pct_sum: dict[int, dict[int, float]] = defaultdict(lambda: defaultdict(float))
        dp_war_pct_n: dict[int, dict[int, int]] = defaultdict(lambda: defaultdict(int))
        dp_row_pct_sum: dict[int, dict[int, float]] = defaultdict(lambda: defaultdict(float))
        dp_row_pct_n: dict[int, dict[int, int]] = defaultdict(lambda: defaultdict(int))
        dp_intel_pct_sum: dict[int, dict[int, float]] = defaultdict(lambda: defaultdict(float))
        dp_intel_pct_n: dict[int, dict[int, int]] = defaultdict(lambda: defaultdict(int))

        # Seed initial VP from player profiles at start_time; also record AI flag
        initial_players_map = gs.states.player_state.players
        current_player_vp: dict[int, int] = {
            pid: int(profile.victory_points)
            for pid, profile in initial_players_map.items()
            if pid > _UNOWNED
        }
        is_native_computer: dict[int, bool] = {
            pid: bool(profile.native_computer)
            for pid, profile in initial_players_map.items()
            if pid > _UNOWNED
        }
        is_computer_player: dict[int, bool] = {
            pid: bool(profile.computer_player)
            for pid, profile in initial_players_map.items()
            if pid > _UNOWNED
        }
        current_player_defeated: dict[int, bool] = {
            pid: bool(profile.defeated)
            for pid, profile in initial_players_map.items()
            if pid > _UNOWNED
        }

        # National morale — running province-level average per player.
        # Maintained incrementally: current_province_morale tracks each province's morale;
        # player_morale_total[player_id] = sum of morale of all owned provinces.
        # Updated on ProvinceChanged morale/owner events; avg = total / province_count.
        current_province_morale: dict[int, float] = {
            pid: float(p.morale) for pid, p in initial_land.items()
        }
        player_morale_total: dict[int, float] = defaultdict(float)
        for pid, morale in current_province_morale.items():
            owner = initial_owners[pid]
            if owner > _UNOWNED:
                player_morale_total[owner] += morale
        player_morale_sum: dict[int, float] = defaultdict(float)
        player_morale_n: dict[int, int] = defaultdict(int)
        morale_pct_sum: dict[int, dict[int, float]] = defaultdict(lambda: defaultdict(float))
        morale_pct_n:   dict[int, dict[int, int]]   = defaultdict(lambda: defaultdict(int))
        morale_day_sum: dict[int, dict[int, float]] = defaultdict(lambda: defaultdict(float))
        morale_day_n:   dict[int, dict[int, int]]   = defaultdict(lambda: defaultdict(int))

        # Elimination timestamps — populated when defeated flips True
        player_elimination_pct: dict[int, float] = {}
        player_elimination_day: dict[int, int] = {}

        # ---- Register hooks — only changed provinces/relations fire events ----
        replay.register_province_trigger(["owner_id", "morale", "resource_production", "money_production", "upgrades_set"])
        replay.register_player_trigger(["victory_points", "defeated", "computer_player"])
        replay.register_foreign_affairs_trigger()

        # ---- Iterate all timestamps ----
        while replay.jump_to_next_patch():
            events = replay.poll_events()
            for event in events.get(ReplayHookTag.ProvinceChanged, []):
                province = event.reference
                pid = province.id
                attrs = event.attributes

                if "owner_id" in attrs:
                    old_owner, new_owner = attrs["owner_id"]
                    ownership_changes[pid] += 1
                    current_owners[pid] = new_owner if new_owner is not None else _UNOWNED
                    if old_owner is not None and old_owner > _UNOWNED:
                        current_player_counts[old_owner] = max(0, current_player_counts[old_owner] - 1)
                        player_losses[old_owner] += 1
                        player_morale_total[old_owner] = max(0.0, player_morale_total[old_owner] - current_province_morale.get(pid, 0.0))
                    if new_owner is not None and new_owner > _UNOWNED:
                        current_player_counts[new_owner] += 1
                        player_captures[new_owner] += 1
                        player_morale_total[new_owner] += current_province_morale.get(pid, 0.0)
                    # Transfer production sums between players
                    for rtype, amount in province_production.get(pid, {}).items():
                        if amount <= 0:
                            continue
                        if old_owner is not None and old_owner > _UNOWNED:
                            current_player_production[old_owner][rtype] = max(
                                0.0, current_player_production[old_owner][rtype] - amount
                            )
                        if new_owner is not None and new_owner > _UNOWNED:
                            current_player_production[new_owner][rtype] += amount
                    # Transfer buildings between players
                    prov_bld = current_province_buildings.get(pid, {})
                    if prov_bld:
                        if old_owner is not None and old_owner > _UNOWNED:
                            for type_key, cnt in prov_bld.items():
                                current_player_buildings[old_owner][type_key] = max(
                                    0, current_player_buildings[old_owner].get(type_key, 0) - cnt
                                )
                        if new_owner is not None and new_owner > _UNOWNED:
                            for type_key, cnt in prov_bld.items():
                                current_player_buildings[new_owner][type_key] += cnt

                if "money_production" in attrs:
                    _, new_mprod = attrs["money_production"]
                    if new_mprod is not None:
                        old_val = province_production.get(pid, {}).get("MONEY", 0.0)
                        new_val = float(int(new_mprod))
                        province_production.setdefault(pid, {})["MONEY"] = new_val
                        owner = current_owners.get(pid, _UNOWNED)
                        if owner > _UNOWNED:
                            current_player_production[owner]["MONEY"] += (new_val - old_val)

                if "resource_production" in attrs:
                    _, new_rprod = attrs["resource_production"]
                    rtype = province_meta[pid]["resource_production_type"]
                    if new_rprod is not None and rtype:
                        old_val = province_production.get(pid, {}).get(rtype, 0.0)
                        new_val = float(int(new_rprod))
                        province_production.setdefault(pid, {})[rtype] = new_val
                        owner = current_owners.get(pid, _UNOWNED)
                        if owner > _UNOWNED:
                            current_player_production[owner][rtype] += (new_val - old_val)

                if "morale" in attrs:
                    _, new_morale = attrs["morale"]
                    if new_morale is not None:
                        morale = float(new_morale)
                        old_prov_morale = current_province_morale.get(pid, 0.0)
                        current_province_morale[pid] = morale
                        owner = current_owners.get(pid, _UNOWNED)
                        if owner > _UNOWNED:
                            player_morale_total[owner] += morale - old_prov_morale
                        prov_morale_sum[pid] = prov_morale_sum.get(pid, 0.0) + morale
                        prov_morale_n[pid] = prov_morale_n.get(pid, 0) + 1
                        if pid in prov_morale_min:
                            prov_morale_min[pid] = min(prov_morale_min[pid], morale)
                            prov_morale_max[pid] = max(prov_morale_max[pid], morale)
                        else:
                            prov_morale_min[pid] = morale
                            prov_morale_max[pid] = morale

                if "upgrades_set" in attrs:
                    old_set, new_set = attrs["upgrades_set"]
                    owner = current_owners.get(pid, _UNOWNED)
                    old_by_id = {u.id: u for u in (old_set or [])}
                    new_by_id = {u.id: u for u in (new_set or [])}
                    for upgrade_id, new_u in new_by_id.items():
                        if not _is_player_building(upgrade_id, ut_map):
                            continue
                        old_u = old_by_id.get(upgrade_id)
                        was_built = _is_built(old_u, ut_map) if old_u is not None else False
                        now_built = _is_built(new_u, ut_map)
                        if not was_built and now_built:
                            type_key = _upgrade_type_key(upgrade_id, ut_map)
                            prov_bld = current_province_buildings.setdefault(pid, {})
                            prov_bld[type_key] = prov_bld.get(type_key, 0) + 1
                            if owner > _UNOWNED:
                                current_player_buildings[owner][type_key] += 1
                        elif was_built and not now_built:
                            type_key = _upgrade_type_key(upgrade_id, ut_map)
                            prov_bld = current_province_buildings.setdefault(pid, {})
                            prov_bld[type_key] = max(0, prov_bld.get(type_key, 0) - 1)
                            if owner > _UNOWNED:
                                current_player_buildings[owner][type_key] = max(
                                    0, current_player_buildings[owner].get(type_key, 0) - 1
                                )
                    for upgrade_id, old_u in old_by_id.items():
                        if upgrade_id not in new_by_id and _is_player_building(upgrade_id, ut_map) and _is_built(old_u, ut_map):
                            type_key = _upgrade_type_key(upgrade_id, ut_map)
                            prov_bld = current_province_buildings.setdefault(pid, {})
                            prov_bld[type_key] = max(0, prov_bld.get(type_key, 0) - 1)
                            if owner > _UNOWNED:
                                current_player_buildings[owner][type_key] = max(
                                    0, current_player_buildings[owner].get(type_key, 0) - 1
                                )

            # Diplomacy — one event per tick when neighbor_relations changed;
            # extractor diffs old vs new to classify per-(sender, receiver) transitions.
            # Use .value comparisons: game state enums may come from a versioned module
            # (e.g. data_types.v210) while the extractor imports from data_types.newest —
            # different classes, so == fails even for identical members.
            _war_val = ForeignAffairRelationTypes.WAR.value
            _peace_val = ForeignAffairRelationTypes.PEACE.value
            _mutual_val = ForeignAffairRelationTypes.MUTUAL_PROTECTION.value
            _row_val = ForeignAffairRelationTypes.RIGHT_OF_WAY.value
            _intel_val = ForeignAffairRelationTypes.SHARED_INTELLIGENCE.value
            for fa_event in events.get(ReplayHookTag.ForeignAffairsRelationChanged, []):
                old_rel, new_rel = fa_event.attributes["neighbor_relations"]
                if old_rel is None or new_rel is None:
                    continue
                # `new_rel` is the full post-change relation matrix — keep a running
                # snapshot (as plain .value ints) so per-tick bucket sampling below
                # can read each player's *current* outgoing relation counts in O(1).
                current_relations = {
                    s: {r: v.value for r, v in row.items()}
                    for s, row in new_rel.items()
                }
                for s in set(old_rel) | set(new_rel):
                    prev_row = old_rel.get(s, {})
                    curr_row = new_rel.get(s, {})
                    for r in set(prev_row) | set(curr_row):
                        old_v = prev_row.get(r)
                        new_v = curr_row.get(r)
                        old_val = old_v.value if old_v is not None else _peace_val
                        new_val = new_v.value if new_v is not None else _peace_val
                        if old_val == new_val:
                            continue
                        sender_id = s + 1
                        if new_val == _war_val:
                            dp_wars[sender_id] += 1
                            game_wars += 1
                        elif old_val == _war_val and new_val >= _peace_val:
                            dp_peace[sender_id] += 1
                            game_peace += 1
                        if new_val == _mutual_val:
                            dp_alliances[sender_id] += 1
                            game_alliances += 1
                        elif old_val == _mutual_val:
                            dp_allianced[sender_id] += 1
                            game_allianced += 1
                        if new_val == _row_val:
                            dp_rows[sender_id] += 1
                            game_rows += 1

            for player_event in events.get(ReplayHookTag.PlayerChanged, []):
                player_profile = player_event.reference
                pid = player_profile.player_id
                if "victory_points" in player_event.attributes:
                    _, new_vp = player_event.attributes["victory_points"]
                    if new_vp is not None:
                        current_player_vp[pid] = int(new_vp)
                if "defeated" in player_event.attributes:
                    _, new_defeated = player_event.attributes["defeated"]
                    if new_defeated is not None:
                        was_defeated = current_player_defeated.get(pid, False)
                        current_player_defeated[pid] = bool(new_defeated)
                        if new_defeated and not was_defeated and pid not in player_elimination_pct:
                            et = replay.current_time
                            if et is not None:
                                elapsed = (et - start_time).total_seconds()
                                player_elimination_pct[pid] = (
                                    (elapsed / total_duration_seconds) * 100.0
                                    if total_duration_seconds > 0 else 0.0
                                )
                                player_elimination_day[pid] = _day_bucket(elapsed, total_duration_seconds, game_days)
                if "computer_player" in player_event.attributes:
                    _, new_cp = player_event.attributes["computer_player"]
                    if new_cp is not None:
                        is_computer_player[pid] = bool(new_cp)

            # Snapshot player territory counts and VP — O(players), not O(provinces)
            ct = replay.current_time
            pb = _pct_bucket((ct - start_time).total_seconds(), total_duration_seconds) if ct else 0
            db = _day_bucket((ct - start_time).total_seconds(), total_duration_seconds, game_days) if ct else 0

            # Integrate production over elapsed time and snapshot for averages/buckets
            if ct is not None:
                delta_days = (ct - prev_time).total_seconds() / 86400.0
                for player_id, rtypes in current_player_production.items():
                    for rtype, rprod in rtypes.items():
                        if rprod > 0:
                            player_total_prod[player_id][rtype] += rprod * delta_days
                prev_time = ct

            for player_id, rtypes in current_player_production.items():
                if not any(v > 0 for v in rtypes.values()):
                    continue
                player_prod_n[player_id] += 1
                for rtype, rprod in rtypes.items():
                    if rprod <= 0:
                        continue
                    player_prod_sum[player_id][rtype] += rprod
                    if rprod > player_peak_prod[player_id].get(rtype, 0.0):
                        player_peak_prod[player_id][rtype] = rprod
                    prod_pct_sum[player_id][rtype][pb] += rprod
                    prod_pct_n[player_id][rtype][pb] += 1
                    prod_day_sum[player_id][rtype][db] += rprod
                    prod_day_n[player_id][rtype][db] += 1

            for player_id, cnt in current_player_counts.items():
                if cnt <= 0:
                    continue
                player_prov_sum[player_id] += cnt
                player_prov_n[player_id] += 1
                player_prov_max[player_id] = max(player_prov_max[player_id], cnt)
                if player_id in player_prov_min:
                    player_prov_min[player_id] = min(player_prov_min[player_id], cnt)
                else:
                    player_prov_min[player_id] = cnt
                pct_bucket_sum[player_id][pb] += cnt
                pct_bucket_n[player_id][pb] += 1
                day_bucket_sum[player_id][db] += cnt
                day_bucket_n[player_id][db] += 1
                vp = current_player_vp.get(player_id, 0)
                pct_vp_bucket_sum[player_id][pb] += vp
                pct_vp_bucket_n[player_id][pb] += 1
                day_vp_bucket_sum[player_id][db] += vp
                day_vp_bucket_n[player_id][db] += 1

                # Diplomatic-state snapshot — counts of this player's *current*
                # outgoing relations by type (sender perspective, mirrors dp_wars/etc.)
                relation_row = current_relations.get(player_id - 1, {})
                war_n = row_n = intel_n = 0
                for rel_val in relation_row.values():
                    if rel_val == _war_val:
                        war_n += 1
                    elif rel_val == _row_val:
                        row_n += 1
                    elif rel_val == _intel_val:
                        intel_n += 1
                dp_war_pct_sum[player_id][pb] += war_n
                dp_war_pct_n[player_id][pb] += 1
                dp_row_pct_sum[player_id][pb] += row_n
                dp_row_pct_n[player_id][pb] += 1
                dp_intel_pct_sum[player_id][pb] += intel_n
                dp_intel_pct_n[player_id][pb] += 1
            n_alive = n_active_human = n_passive_human = n_ai = 0
            for pid, defeated in current_player_defeated.items():
                if defeated:
                    continue
                n_alive += 1
                computer = is_computer_player.get(pid, False)
                native = is_native_computer.get(pid, False)
                if not computer and not native:
                    n_active_human += 1
                elif computer and not native:
                    n_passive_human += 1
                elif computer and native:
                    n_ai += 1
            pct_alive_sum[pb] += n_alive
            pct_alive_n[pb] += 1
            pct_active_human_sum[pb] += n_active_human
            pct_active_human_n[pb] += 1
            pct_passive_human_sum[pb] += n_passive_human
            pct_passive_human_n[pb] += 1
            pct_ai_sum[pb] += n_ai
            pct_ai_n[pb] += 1
            day_alive_sum[db] += n_alive
            day_alive_n[db] += 1
            day_active_human_sum[db] += n_active_human
            day_active_human_n[db] += 1
            day_passive_human_sum[db] += n_passive_human
            day_passive_human_n[db] += 1
            day_ai_sum[db] += n_ai
            day_ai_n[db] += 1

            # Building time-series snapshot (O(players × building_types) — no province scan).
            # Snapshot per Building Type ((uid, tier)) directly, and derive the Building Group
            # (uid) snapshot by summing tier counts so its avg/n semantics stay unchanged.
            for player_id, type_counts in current_player_buildings.items():
                uid_totals: dict[str, int] = defaultdict(int)
                for (uid, tier), cnt in type_counts.items():
                    if cnt > 0:
                        uid_totals[uid] += cnt
                        bldtype_pct_sum[player_id][(uid, tier)][pb] += cnt
                        bldtype_pct_n[player_id][(uid, tier)][pb] += 1
                for uid, total in uid_totals.items():
                    bld_pct_sum[player_id][uid][pb] += total
                    bld_pct_n[player_id][uid][pb] += 1

            # National morale snapshot — average province morale per player
            for player_id, total_morale in player_morale_total.items():
                count = current_player_counts.get(player_id, 0)
                if count <= 0 or current_player_defeated.get(player_id, False):
                    continue
                avg_morale = total_morale / count
                if avg_morale > 0:
                    player_morale_sum[player_id] += avg_morale
                    player_morale_n[player_id] += 1
                    morale_pct_sum[player_id][pb] += avg_morale
                    morale_pct_n[player_id][pb] += 1
                    morale_day_sum[player_id][db] += avg_morale
                    morale_day_n[player_id][db] += 1

        # ---- Final state — game_state accessed once, only for production values ----
        gs = replay.game_state
        if gs is None:
            raise ValueError("game_state is None at end of replay")

        final_land = {
            pid: p
            for pid, p in gs.states.map_state.map.provinces.items()
            if _is_land_province(p)
        }

        # ---- Building level scan (once on final_land) ----
        bld_tier_count: dict[int, dict[str, dict[int, int]]] = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
        for _pid, _p in final_land.items():
            _owner = current_owners.get(_pid, _UNOWNED)
            if _owner <= _UNOWNED:
                continue
            for _upgrade in (getattr(_p, "upgrades", None) or {}).values():
                if not _is_player_building(_upgrade.id, ut_map) or not _is_built(_upgrade, ut_map):
                    continue
                _uid = _upgrade_identifier(_upgrade.id, ut_map)
                _ut = ut_map.get(_upgrade.id)
                if _ut is not None:
                    bld_level_sum[_owner][_uid] += _ut.tier
                    bld_level_n[_owner][_uid] += 1
                    bld_tier_count[_owner][_uid][_ut.tier] += 1

        # ---- Players ----
        players_map = gs.states.player_state.players

        initial_player_counts: dict[int, int] = defaultdict(int)
        for oid in initial_owners.values():
            if oid > _UNOWNED:
                initial_player_counts[oid] += 1

        players: list[PlayerData] = []
        for player_id, profile in players_map.items():
            # Skip system/neutral slots (pid <= 0) and Guest placeholder
            if player_id <= 0 or not profile.nation_name or profile.name == "Guest":
                continue
            n = player_prov_n.get(player_id, 1)
            n_prod = player_prod_n.get(player_id, 1)
            players.append(PlayerData(
                player_id=player_id,
                nation_name=profile.nation_name,
                player_name=profile.name,
                team_id=profile.team_id,
                is_ai=bool(profile.computer_player),
                is_defeated=bool(profile.defeated),
                is_playing=bool(profile.playing),
                final_vp=int(profile.victory_points),
                initial_province_count=initial_player_counts.get(player_id, 0),
                final_province_count=current_player_counts.get(player_id, 0),
                max_province_count=player_prov_max.get(player_id, 0),
                min_province_count=player_prov_min.get(player_id, 0),
                avg_province_count=player_prov_sum.get(player_id, 0) / n,
                provinces_captured=player_captures.get(player_id, 0),
                provinces_lost=player_losses.get(player_id, 0),
                pct_buckets=_finalize_buckets(pct_bucket_sum[player_id], pct_bucket_n[player_id]),
                day_buckets=_finalize_buckets(day_bucket_sum[player_id], day_bucket_n[player_id]),
                pct_vp_buckets=_finalize_buckets(pct_vp_bucket_sum[player_id], pct_vp_bucket_n[player_id]),
                day_vp_buckets=_finalize_buckets(day_vp_bucket_sum[player_id], day_vp_bucket_n[player_id]),
                wars_declared=dp_wars.get(player_id, 0),
                peace_treaties_signed=dp_peace.get(player_id, 0),
                alliances_formed=dp_alliances.get(player_id, 0),
                alliance_dissolutions=dp_allianced.get(player_id, 0),
                right_of_ways_signed=dp_rows.get(player_id, 0),
                avg_production_by_type={
                    rtype: player_prod_sum[player_id][rtype] / n_prod
                    for rtype in player_prod_sum.get(player_id, {})
                },
                total_production_by_type=dict(player_total_prod.get(player_id, {})),
                peak_production_by_type=dict(player_peak_prod.get(player_id, {})),
                production_pct_buckets={
                    rtype: _finalize_float_buckets(prod_pct_sum[player_id][rtype], prod_pct_n[player_id][rtype])
                    for rtype in prod_pct_sum.get(player_id, {})
                },
                production_day_buckets={
                    rtype: _finalize_float_buckets(prod_day_sum[player_id][rtype], prod_day_n[player_id][rtype])
                    for rtype in prod_day_sum.get(player_id, {})
                },
                final_building_counts=_group_building_counts(current_player_buildings.get(player_id, {})),
                final_building_levels={
                    uid: bld_level_sum[player_id][uid] / bld_level_n[player_id][uid]
                    for uid in bld_level_sum.get(player_id, {})
                    if bld_level_n[player_id][uid] > 0
                },
                final_building_tier_counts={
                    uid: dict(tier_counts)
                    for uid, tier_counts in bld_tier_count.get(player_id, {}).items()
                },
                building_pct_buckets={
                    uid: _finalize_float_buckets(bld_pct_sum[player_id][uid], bld_pct_n[player_id][uid])
                    for uid in bld_pct_sum.get(player_id, {})
                },
                building_type_pct_buckets={
                    type_key: _finalize_float_buckets(bldtype_pct_sum[player_id][type_key], bldtype_pct_n[player_id][type_key])
                    for type_key in bldtype_pct_sum.get(player_id, {})
                },
                pct_bucket_coverage=dict(pct_bucket_n[player_id]),
                elimination_game_pct=player_elimination_pct.get(player_id),
                elimination_game_day=player_elimination_day.get(player_id),
                avg_national_morale=(
                    player_morale_sum[player_id] / player_morale_n[player_id]
                    if player_morale_n.get(player_id, 0) > 0 else 0.0
                ),
                morale_pct_buckets=_finalize_float_buckets(morale_pct_sum[player_id], morale_pct_n[player_id]),
                morale_day_buckets=_finalize_float_buckets(morale_day_sum[player_id], morale_day_n[player_id]),
                at_war_pct_buckets=_finalize_float_buckets(dp_war_pct_sum[player_id], dp_war_pct_n[player_id]),
                right_of_way_pct_buckets=_finalize_float_buckets(dp_row_pct_sum[player_id], dp_row_pct_n[player_id]),
                shared_intelligence_pct_buckets=_finalize_float_buckets(dp_intel_pct_sum[player_id], dp_intel_pct_n[player_id]),
            ))

        # ---- Victory detection ----
        winner_ids, victory_type = _determine_winners(players)

        # ---- Provinces ----
        provinces: list[ProvinceData] = []
        for pid, pmeta in province_meta.items():
            final_p = final_land.get(pid)
            n = prov_morale_n.get(pid, 1)
            provinces.append(ProvinceData(
                province_id=pid,
                province_name=pmeta["name"],
                terrain_type=pmeta["terrain_type"],
                is_coastal=pmeta["is_coastal"],
                initial_owner_id=initial_owners.get(pid, -1),
                final_owner_id=current_owners.get(pid, -1),
                ownership_changes=ownership_changes.get(pid, 0),
                resource_production_type=pmeta["resource_production_type"],
                resource_production=int(final_p.resource_production or 0) if final_p else 0,
                money_production=int(final_p.money_production) if final_p else 0,
                avg_morale=prov_morale_sum.get(pid, 0.0) / n,
                min_morale=prov_morale_min.get(pid, 0.0),
                max_morale=prov_morale_max.get(pid, 0.0),
                final_upgrade_counts=dict(current_province_buildings.get(pid, {})),
            ))

        game_total_prod: dict[str, float] = defaultdict(float)
        for player in players:
            for rtype, val in player.total_production_by_type.items():
                game_total_prod[rtype] += val

        return GameData(
            game_id=game_id,
            map_id=map_id,
            file_path=str(file_path),
            start_time=start_time,
            end_time=end_time,
            game_days=game_days,
            total_updates=total_updates,
            avg_update_interval_seconds=avg_update_interval_seconds,
            winner_ids=winner_ids,
            victory_type=victory_type,
            game_ended=True,  # guaranteed by early exit in extract()
            players=players,
            provinces=provinces,
            total_wars_declared=game_wars,
            total_peace_treaties=game_peace,
            total_alliances_formed=game_alliances,
            total_alliance_dissolutions=game_allianced,
            total_right_of_ways=game_rows,
            pct_alive_buckets=_finalize_buckets(pct_alive_sum, pct_alive_n),
            pct_active_human_buckets=_finalize_buckets(pct_active_human_sum, pct_active_human_n),
            pct_passive_human_buckets=_finalize_buckets(pct_passive_human_sum, pct_passive_human_n),
            pct_ai_buckets=_finalize_buckets(pct_ai_sum, pct_ai_n),
            day_alive_buckets=_finalize_buckets(day_alive_sum, day_alive_n),
            day_active_human_buckets=_finalize_buckets(day_active_human_sum, day_active_human_n),
            day_passive_human_buckets=_finalize_buckets(day_passive_human_sum, day_passive_human_n),
            day_ai_buckets=_finalize_buckets(day_ai_sum, day_ai_n),
            game_total_production=dict(game_total_prod),
        )


def _determine_winners(players: list[PlayerData]) -> tuple[list[int], str]:
    if not players:
        return [], "unknown"

    # Prefer still-playing non-defeated players as the winner pool
    still_playing = [p for p in players if p.is_playing and not p.is_defeated]

    if len(still_playing) == 1:
        return [still_playing[0].player_id], "solo"

    if len(still_playing) >= 2:
        # All on same team → coalition
        team_ids = {p.team_id for p in still_playing if p.team_id > 0}
        if len(team_ids) == 1 and all(p.team_id > 0 for p in still_playing):
            return [p.player_id for p in still_playing], "coalition"

    # Fallback: use VP among non-defeated (covers games where playing flag is unreliable)
    pool = still_playing or [p for p in players if not p.is_defeated] or players
    max_vp = max((p.final_vp for p in pool), default=0)
    if max_vp <= 0:
        return [], "unknown"

    threshold = max_vp * 0.9
    winners = [p for p in pool if p.final_vp >= threshold]

    if len(winners) == 1:
        return [winners[0].player_id], "solo"

    team_ids = {p.team_id for p in winners if p.team_id > 0}
    if len(team_ids) == 1:
        return [p.player_id for p in winners], "coalition"

    top = max(winners, key=lambda p: p.final_vp)
    return [top.player_id], "solo"
