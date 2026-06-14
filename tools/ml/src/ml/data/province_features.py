"""
Per-province node feature vector for the GNN.

`build_province_feature_vector()` dispatches on `isinstance(province, LandProvince)`.
Fields that don't apply to the other province type are encoded as zero. Enum one-hots
match members by `.value` rather than identity/equality, since game-state objects can
come from a different `data_types.vXXX` module than the one imported here (see
[[feedback_versioned_enum_comparison]]).
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
from conflict_interface.data_types.newest.common.enums.region_type import RegionType
from conflict_interface.data_types.newest.map_state.land_province import LandProvince
from conflict_interface.data_types.newest.map_state.map_state_enums import (
    ProvinceStateID,
    ResourceProductionType,
    TerrainType,
)
from conflict_interface.data_types.newest.map_state.sea_province import SeaProvince

_BUILDING_VOCAB_PATH = Path(__file__).parent / "building_vocab.json"
BUILDING_VOCAB: list[str] = json.loads(_BUILDING_VOCAB_PATH.read_text(encoding="utf-8"))
BUILDING_VOCAB_INDEX: dict[str, int] = {name: i for i, name in enumerate(BUILDING_VOCAB)}

_TERRAIN_TYPES = list(TerrainType)
_PROVINCE_STATE_IDS = list(ProvinceStateID)
_RESOURCE_PRODUCTION_TYPES = list(ResourceProductionType)
_REGION_TYPES = [r for r in RegionType if r.value != RegionType.NONE.value]

# is_sea, is_capital, resource_production, money_production, victory_points, morale,
# costal, has_construction
_NUM_SCALAR_FEATURES = 8

NUM_PROVINCE_FEATURES = (
    _NUM_SCALAR_FEATURES
    + len(_TERRAIN_TYPES)
    + len(_PROVINCE_STATE_IDS)
    + len(_RESOURCE_PRODUCTION_TYPES)
    + len(_REGION_TYPES)
    + len(BUILDING_VOCAB)
)

# Upgrades that have resource costs but aren't persistent buildings (one-time actions).
_NON_BUILDING_NAMES = frozenset({"Annex City", "Relocate Headquarters", "Nationalize"})


def _one_hot(members: list, value) -> np.ndarray:
    vec = np.zeros(len(members), dtype=np.float32)
    if value is None:
        return vec
    value_val = getattr(value, "value", value)
    for i, member in enumerate(members):
        if member.value == value_val:
            vec[i] = 1.0
            break
    return vec


def _multi_hot(members: list, values) -> np.ndarray:
    vec = np.zeros(len(members), dtype=np.float32)
    if not values:
        return vec
    member_vals = [m.value for m in members]
    for value in values:
        value_val = getattr(value, "value", value)
        for i, member_val in enumerate(member_vals):
            if member_val == value_val:
                vec[i] = 1.0
                break
    return vec


def _is_player_building(upgrade_type) -> bool:
    if upgrade_type.upgrade_name in _NON_BUILDING_NAMES:
        return False
    return bool(upgrade_type.costs)


def _is_built(upgrade, upgrade_type) -> bool:
    condition = upgrade.condition
    if condition is None or condition <= 0:
        return False
    return condition >= upgrade_type.build_condition


def _building_key(upgrade_type) -> str:
    identifier = upgrade_type.upgrade_identifier or upgrade_type.upgrade_name or str(upgrade_type.id)
    identifier = identifier.replace(" ", "_").replace("-", "_")
    return f"{identifier}_t{upgrade_type.tier}"


def _building_counts(province: LandProvince, ut_map: dict) -> np.ndarray:
    vec = np.zeros(len(BUILDING_VOCAB), dtype=np.float32)
    for upgrade in province.upgrades_set or []:
        upgrade_type = ut_map.get(upgrade.id)
        if upgrade_type is None:
            continue
        if not _is_player_building(upgrade_type) or not _is_built(upgrade, upgrade_type):
            continue
        idx = BUILDING_VOCAB_INDEX.get(_building_key(upgrade_type))
        if idx is not None:
            vec[idx] += 1.0
    return vec


def build_province_feature_vector(
    province: LandProvince | SeaProvince,
    ut_map: dict,
    capital_province_ids: set[int],
) -> np.ndarray:
    """Build the per-province node feature vector (land + sea share one schema)."""
    is_land = isinstance(province, LandProvince)

    if is_land:
        is_capital = 1.0 if province.id in capital_province_ids else 0.0
        province_state_vec = _one_hot(_PROVINCE_STATE_IDS, province.province_state_id)
        resource_type_vec = _one_hot(_RESOURCE_PRODUCTION_TYPES, province.resource_production_type)
        resource_production = math.log1p(max(0, province.resource_production or 0))
        money_production = math.log1p(max(0, province.money_production or 0))
        victory_points = math.log1p(max(0, province.victory_points or 0))
        morale = float(province.morale) / 100.0
        costal = 1.0 if province.costal else 0.0
        building_vec = _building_counts(province, ut_map)
        has_construction = 1.0 if (province.constructions and province.constructions[0] is not None) else 0.0
    else:
        is_capital = 0.0
        province_state_vec = np.zeros(len(_PROVINCE_STATE_IDS), dtype=np.float32)
        resource_type_vec = _one_hot(_RESOURCE_PRODUCTION_TYPES, ResourceProductionType.NONE)
        resource_production = 0.0
        money_production = 0.0
        victory_points = 0.0
        morale = 0.0
        costal = 0.0
        building_vec = np.zeros(len(BUILDING_VOCAB), dtype=np.float32)
        has_construction = 0.0

    terrain_vec = _one_hot(_TERRAIN_TYPES, province.terrain_type)
    region_vec = _multi_hot(_REGION_TYPES, province.region)

    scalars = np.array(
        [
            0.0 if is_land else 1.0,  # is_sea
            is_capital,
            resource_production,
            money_production,
            victory_points,
            morale,
            costal,
            has_construction,
        ],
        dtype=np.float32,
    )

    return np.concatenate([scalars, terrain_vec, province_state_vec, resource_type_vec, region_vec, building_vec])


def build_owner_seat_idx(province: LandProvince | SeaProvince, seat_idx: dict[int, int]) -> int:
    """Seat index for the province's owner (land) / legal owner (sea); seat 0 = neutral."""
    if isinstance(province, LandProvince):
        owner_id = province.owner_id
    else:
        owner_id = province.legal_owner
    return seat_idx.get(owner_id, 0) if owner_id is not None else 0
