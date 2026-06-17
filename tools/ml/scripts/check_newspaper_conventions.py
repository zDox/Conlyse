#!/usr/bin/env python3
"""
Validates newspaper_features.py classifiers against hardcoded fixtures derived
from real replay data, then optionally scans actual .conrp files for hit-count
sanity checks.

Usage:
    # Fast fixture assertions only (no replay files needed):
    python tools/ml/scripts/check_newspaper_conventions.py

    # Full real-data scan:
    python tools/ml/scripts/check_newspaper_conventions.py \\
        --replays-dir data/ml/replays/training_set \\
        --maps-dir data/maps_dir \\
        --max-replays 20
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path
from types import SimpleNamespace

# ---------------------------------------------------------------------------
# Fixtures — SimpleNamespace stubs that match the real article shape
# ---------------------------------------------------------------------------

def _article(title="", author="", message_body="", sender_id=-1, receiver_id=-1, time_stamp=0, day=1):
    return SimpleNamespace(
        title=title,
        author=author,
        message_body=message_body,
        sender_id=sender_id,
        receiver_id=receiver_id,
        time_stamp=time_stamp,
        day=day,
    )


class _FakeStatisticsArticle:
    """Stub for StatisticsArticle — classify_article must return []."""
    title = "Trending"
    author = "Editor"
    message_body = ""
    sender_id = -1
    receiver_id = -1
    time_stamp = 0


# Casualty article: two <p> segments — unit loss + building damage for player 1
FIXTURE_CASUALTY = _article(
    title="3rd Motorized Battalion (Russia) reports casualties",
    author="",
    sender_id=17,
    receiver_id=-1,
    message_body=(
        "<p>Units of Russia lost: 2 Motorized Infantry over {{{provLink 'Moscow'}}}.</p>"
        "<p>Building damaged in {{{provLink 'Moscow'}}}: Arms Industry.</p>"
    ),
)

# Veteran recruitment for player 2
FIXTURE_VETERAN = _article(
    title="{{{provLink 'Berlin'}}} recruits new Armored Fighting Vehicle Veteran.",
    author="",
    sender_id=5,
    receiver_id=-1,
    message_body="Germany builds new Basic AFV Veteran \"Ironclad\".",
)

# Nuclear ICBM attack: sender=17 (Russia), receiver=6 (India)
FIXTURE_NUCLEAR = _article(
    title="Nuclear ICBM attack on India",
    author="",
    sender_id=17,
    receiver_id=6,
    message_body="<p>Russia launched a Nuclear ICBM at India.</p>",
)

# Insurgent attack on player 3
FIXTURE_INSURGENT = _article(
    title="Poland hit by insurgent attack",
    author="BREAKING NEWS: Violent Insurgency",
    sender_id=8,
    receiver_id=-1,
    message_body="<p>Insurgents attacked Poland.</p>",
)

# Dissent event for player 4
FIXTURE_DISSENT = _article(
    title="Widespread Dissent in Japan",
    author="Crimes against Humanity",
    sender_id=3,
    receiver_id=-1,
    message_body="<p>Citizens of Japan are unhappy.</p>",
)

# Casualty with unknown unit name (should land only in catch-all, not KeyError)
FIXTURE_UNKNOWN_UNIT = _article(
    title="Some battle (France) reports casualties",
    author="",
    sender_id=2,
    receiver_id=-1,
    message_body="<p>Units of France lost: 1 FutureUnitXYZ over {{{provLink 'Paris'}}}.</p>",
)

# StatisticsArticle stub — must return []
FIXTURE_STATISTICS = _FakeStatisticsArticle()


# ---------------------------------------------------------------------------
# Fixture assertions
# ---------------------------------------------------------------------------

def run_fixture_assertions() -> None:
    from ml.data.newspaper_features import (
        NUM_UNIT_TYPES,
        UNIT_VOCAB_INDEX,
        classify_article,
        compute_newspaper_features,
    )

    print("Running fixture assertions...")

    # --- StatisticsArticle returns [] ---
    assert classify_article(FIXTURE_STATISTICS) == [], "StatisticsArticle must return []"

    # --- Casualty: Motorized Infantry losses go to UNIT_VOCAB_INDEX slot ---
    mi_idx = UNIT_VOCAB_INDEX.get("Motorized Infantry")
    assert mi_idx is not None, "'Motorized Infantry' must be in UNIT_VOCAB"
    events = classify_article(FIXTURE_CASUALTY)
    by_idx = {e.feature_idx: e for e in events if e.player_id == 17}
    assert mi_idx in by_idx, f"Expected Motorized Infantry at idx {mi_idx}"
    assert by_idx[mi_idx].weight == 2.0, "Expected weight=2 for 'lost: 2 Motorized Infantry'"
    buildings_idx = NUM_UNIT_TYPES + 0
    assert buildings_idx in by_idx, "Expected buildings_damaged event"
    catchall_idx = NUM_UNIT_TYPES + 6
    assert catchall_idx in by_idx, "Expected catch-all event from casualty"

    # --- Veteran recruitment ---
    events = classify_article(FIXTURE_VETERAN)
    idxs = {e.feature_idx for e in events}
    assert NUM_UNIT_TYPES + 1 in idxs, "Expected veterans_recruited"
    assert NUM_UNIT_TYPES + 6 in idxs, "Expected catch-all from veteran"
    assert all(e.player_id == 5 for e in events), "All events must be attributed to sender_id=5"

    # --- Nuclear attack: both attacker and victim ---
    events = classify_article(FIXTURE_NUCLEAR)
    launched = [e for e in events if e.feature_idx == NUM_UNIT_TYPES + 2]
    received = [e for e in events if e.feature_idx == NUM_UNIT_TYPES + 3]
    assert len(launched) == 1 and launched[0].player_id == 17, "nuclear_launched must be sender"
    assert len(received) == 1 and received[0].player_id == 6, "nuclear_received must be receiver"

    # --- Insurgent attack ---
    events = classify_article(FIXTURE_INSURGENT)
    idxs = {e.feature_idx for e in events}
    assert NUM_UNIT_TYPES + 4 in idxs, "Expected insurgent_attacks"
    assert NUM_UNIT_TYPES + 6 in idxs, "Expected catch-all from insurgent"

    # --- Dissent ---
    events = classify_article(FIXTURE_DISSENT)
    idxs = {e.feature_idx for e in events}
    assert NUM_UNIT_TYPES + 5 in idxs, "Expected dissent_events"

    # --- Unknown unit name: catch-all only, no KeyError ---
    events = classify_article(FIXTURE_UNKNOWN_UNIT)
    idxs = {e.feature_idx for e in events}
    assert NUM_UNIT_TYPES + 6 in idxs, "Catch-all must fire even for unknown unit name"
    # No per-unit-type slot should have fired (FutureUnitXYZ is not in vocab)
    unit_events = [e for e in events if e.feature_idx < NUM_UNIT_TYPES]
    assert len(unit_events) == 0, f"Unknown unit name must not match any vocab slot, got {unit_events}"

    # --- compute_newspaper_features: sender_id not in seat_idx is silently dropped ---
    seat_idx = {17: 1, 5: 2}  # player 17 → seat 1, player 5 → seat 2
    # FIXTURE_CASUALTY has sender_id=17 (in seat_idx), FIXTURE_VETERAN has sender_id=5 (in seat_idx)
    # FIXTURE_NUCLEAR has receiver=6 (NOT in seat_idx) — must not raise KeyError
    articles = [FIXTURE_CASUALTY, FIXTURE_VETERAN, FIXTURE_NUCLEAR, FIXTURE_STATISTICS]
    feats = compute_newspaper_features(articles, seat_idx, num_players=2)
    assert feats.shape == (2, NUM_UNIT_TYPES + 7), f"Expected shape (2, {NUM_UNIT_TYPES + 7}), got {feats.shape}"
    # player 0 (seat 1, id=17): should have Motorized Infantry loss and nuclear_launched
    assert feats[0, mi_idx] > 0, "Player 17 should have Motorized Infantry losses"
    assert feats[0, NUM_UNIT_TYPES + 2] > 0, "Player 17 should have nuclear_launched"
    # player 1 (seat 2, id=5): should have veterans_recruited
    assert feats[1, NUM_UNIT_TYPES + 1] > 0, "Player 5 should have veterans_recruited"

    print(f"  All fixture assertions passed ({NUM_UNIT_TYPES} unit types in vocab).")


# ---------------------------------------------------------------------------
# Optional real-data scan
# ---------------------------------------------------------------------------

def run_replay_scan(replays_dir: Path, maps_dir: Path, max_replays: int) -> None:
    from conflict_interface.interface.replay_interface import ReplayInterface
    from ml.data.newspaper_features import FEATURE_NAMES, classify_article

    print(f"\nScanning up to {max_replays} replays in {replays_dir} ...")

    static_map_data = {p.stem: p for p in maps_dir.glob("*.bin")}
    replay_files = sorted(replays_dir.glob("*.conrp"))[:max_replays]
    if not replay_files:
        print("  No .conrp files found — skipping scan.")
        return

    total_articles = 0
    total_classified = 0
    hits: Counter = Counter()

    for replay_path in replay_files:
        ritf = ReplayInterface(replay_path, static_map_data=static_map_data)
        try:
            if not ritf.open():
                continue
            ritf.jump_to(ritf.last_time)
            gs = ritf.game_state
            if gs is None or gs.states.newspaper_state is None:
                continue
            articles = list(gs.states.newspaper_state.articles)
            total_articles += len(articles)
            for article in articles:
                events = classify_article(article)
                if events:
                    total_classified += 1
                    for e in events:
                        hits[e.feature_idx] += 1
        finally:
            ritf.close()

    print(f"  {len(replay_files)} replays, {total_articles} articles, {total_classified} classified")
    print("\n  Per-feature hit counts (top 20):")
    for idx, count in hits.most_common(20):
        name = FEATURE_NAMES[idx] if idx < len(FEATURE_NAMES) else f"idx_{idx}"
        print(f"    [{idx:3d}] {name:<40s} {count}")
    if not hits:
        print("  WARNING: zero articles classified — check regex patterns.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--replays-dir", type=Path, help="Directory of .conrp files for real-data scan")
    parser.add_argument("--maps-dir", type=Path, help="Directory of static map .bin files")
    parser.add_argument("--max-replays", type=int, default=20, help="Max replays to scan (default: 20)")
    args = parser.parse_args()

    run_fixture_assertions()

    if args.replays_dir:
        if args.maps_dir is None:
            print("ERROR: --maps-dir is required when --replays-dir is specified", file=sys.stderr)
            sys.exit(1)
        run_replay_scan(args.replays_dir, args.maps_dir, args.max_replays)

    print("\nDone.")


if __name__ == "__main__":
    main()
