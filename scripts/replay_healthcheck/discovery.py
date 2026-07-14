"""Local-folder replay discovery."""

from pathlib import Path

from .models import ReplayRow


def _parse_game_player_id(name: str) -> tuple[int | None, int | None]:
    stem = Path(name).stem  # game_<id>_player_<id>
    parts = stem.split("_")
    if len(parts) >= 4:
        return int(parts[1]), int(parts[3])
    return None, None


def discover_replays(replays_dir: Path) -> list[ReplayRow]:
    """Find game_<id>_player_<id>.conrp files in a local directory."""
    files = sorted(replays_dir.glob("game_*_player_*.conrp"))
    rows: list[ReplayRow] = []
    for path in files:
        game_id, player_id = _parse_game_player_id(path.name)
        rows.append(ReplayRow(game_id=game_id, player_id=player_id, path=path))

    print(f"  Found {len(rows)} replay file(s) in {replays_dir}", flush=True)
    return rows
