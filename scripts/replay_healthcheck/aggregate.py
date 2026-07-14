"""Cross-replay aggregation helpers."""

from collections import Counter, defaultdict

from .models import ReplayHealth


def province_consistency(results: list[ReplayHealth]) -> dict[str, dict]:
    """Group replays by map_id and compare each replay's province set against
    the authoritative set from static map data."""
    by_map: dict[str, list[ReplayHealth]] = defaultdict(list)
    for r in results:
        if r.map_id and r.province_ids is not None:
            by_map[r.map_id].append(r)

    consistency: dict[str, dict] = {}
    for map_id, entries in by_map.items():
        expected_sets = [r.expected_province_ids for r in entries if r.expected_province_ids]
        expected = expected_sets[0] if expected_sets else None
        counts = [len(r.province_ids) for r in entries]
        missing_counter: Counter = Counter()
        if expected is not None:
            for r in entries:
                missing_counter.update(expected - r.province_ids)
        consistency[map_id] = {
            "n_games": len(entries),
            "expected_count": len(expected) if expected is not None else None,
            "counts": counts,
            "missing_counter": missing_counter,
        }
    return consistency
