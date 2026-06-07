"""
Per-player, per-snapshot training rows for win-probability ML.

One row = one player at one observed 5%-game-progress bucket in one game.
Rows are only emitted for buckets that have actual replay data (no interpolation).

With 1 000 games × 64 players × ~18 observed buckets ≈ 1.15 M rows.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .intermediate import GameData

RESOURCE_TYPES = ["MONEY", "SUPPLY", "FUEL", "COMPONENT", "ELECTRONIC", "RARE_MATERIAL"]


@dataclass
class TrainingRow:
    game_id: int
    player_id: int
    nation_name: str
    pct_game: int           # 0, 5, 10, … 95 — bucket key

    # Coverage: how many update ticks contributed to this bucket's average.
    # Low values (1) indicate a sparse recording window; use --min-bucket-coverage
    # to exclude them from training.
    bucket_coverage: int

    # Territory
    province_count: int

    # Victory Points at this bucket (averaged over ticks in the window)
    vp: int

    # Production rates (units/day, averaged over ticks in the bucket)
    production: dict[str, float] = field(default_factory=dict)

    # National morale (average province morale for this player, averaged over ticks)
    national_morale: float = 0.0

    # Buildings (average count per building type over ticks in the bucket)
    building_counts: dict[str, float] = field(default_factory=dict)

    # Player type
    is_ai: bool = False

    # Game context
    total_players: int = 0

    # Label — True if this player is in GameData.winner_ids
    is_winner: bool = False

    def to_dict(self) -> dict:
        d = {
            "game_id": self.game_id,
            "player_id": self.player_id,
            "nation_name": self.nation_name,
            "pct_game": self.pct_game,
            "bucket_coverage": self.bucket_coverage,
            "province_count": self.province_count,
            "vp": self.vp,
            "national_morale": self.national_morale,
            "is_ai": int(self.is_ai),
            "total_players": self.total_players,
            "is_winner": int(self.is_winner),
        }
        for rtype in RESOURCE_TYPES:
            d[f"{rtype.lower()}_production"] = self.production.get(rtype, 0.0)
        for uid, count in self.building_counts.items():
            col = "bld_" + uid.replace(" ", "_").replace("-", "_")
            d[col] = count
        return d


def training_rows_from_game_data(
    game: "GameData",
    min_coverage: int = 1,
) -> list[TrainingRow]:
    """
    Convert a finished GameData into a list of TrainingRow, one per
    (player, observed pct_bucket).  Only emits rows for buckets where
    pct_bucket_coverage[pct] >= min_coverage.  No replay file is opened.
    """
    winner_ids = set(game.winner_ids)
    total_players = len(game.players)
    rows: list[TrainingRow] = []

    for player in game.players:
        coverage = player.pct_bucket_coverage
        if not coverage:
            continue  # no data (Guest / neutral / system slot)

        for pct, n_ticks in coverage.items():
            if n_ticks < min_coverage:
                continue
            if pct not in player.pct_buckets:
                continue  # should not happen, but guard anyway

            prod: dict[str, float] = {}
            for rtype in RESOURCE_TYPES:
                bucket_map = player.production_pct_buckets.get(rtype, {})
                if pct in bucket_map:
                    prod[rtype] = bucket_map[pct]

            bld: dict[str, float] = {}
            for uid, bucket_map in player.building_pct_buckets.items():
                if pct in bucket_map:
                    bld[uid] = bucket_map[pct]

            rows.append(TrainingRow(
                game_id=game.game_id,
                player_id=player.player_id,
                nation_name=player.nation_name,
                pct_game=pct,
                bucket_coverage=n_ticks,
                province_count=player.pct_buckets[pct],
                vp=player.pct_vp_buckets.get(pct, 0),
                production=prod,
                national_morale=player.morale_pct_buckets.get(pct, 0.0),
                building_counts=bld,
                is_ai=player.is_ai,
                total_players=total_players,
                is_winner=player.player_id in winner_ids,
            ))

    return rows


# Module-level worker function — must be importable by multiprocessing.
#
# Converts straight to row dicts inside the worker process so only the small
# per-row payload is pickled back to the main process, instead of the full
# GameData (which carries every player's per-tick bucket history).
def training_rows_worker(args: tuple[Path, Path | None, int]) -> tuple[list[dict], bool]:
    file_path, map_data_dir, min_coverage = args

    from ..extractors.replay_extractor import ReplayExtractor

    extractor = ReplayExtractor(map_data_dir=map_data_dir)
    game = extractor.extract_safe(file_path)
    if game is None:
        return [], False

    rows = training_rows_from_game_data(game, min_coverage=min_coverage)
    return [row.to_dict() for row in rows], True
