"""Terminal report."""

from collections import Counter
from datetime import UTC, datetime, timedelta

from .aggregate import province_consistency
from .analyze import GAP_FACTOR
from .models import ReplayHealth, Status

SEP = "=" * 140
SUBSEP = "-" * 140


def strip_tz(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if hasattr(dt, "tzinfo") and dt.tzinfo is not None:
        return dt.astimezone(UTC).replace(tzinfo=None)
    return dt


def fmt_td(td: timedelta | None, *, unit: str = "h") -> str:
    if td is None:
        return "?"
    total_s = td.total_seconds()
    sign = "-" if total_s < 0 else ""
    total_s = abs(total_s)
    if unit == "h":
        h = int(total_s // 3600)
        m = int((total_s % 3600) // 60)
        return f"{sign}{h}h{m:02d}m"
    if unit == "d":
        d = int(total_s // 86400)
        h = int((total_s % 86400) // 3600)
        return f"{sign}{d}d{h:02d}h"
    return f"{sign}{total_s:.0f}s"


def _avg_td(tds: list[timedelta]) -> timedelta:
    return timedelta(seconds=sum(t.total_seconds() for t in tds) / len(tds))


def print_report(results: list[ReplayHealth]) -> None:
    print(f"\n{SEP}")
    print(f"REPLAY HEALTH CHECK  —  {len(results)} replays")
    print(SEP)

    # ── Status breakdown ──────────────────────────────────────────────────
    status_counts = Counter(r.status for r in results)
    print("\nSTATUS")
    print(SUBSEP)
    for status in (Status.OK, Status.DEGRADED, Status.FAILED):
        print(f"  {status.value:<9} {status_counts.get(status, 0)}/{len(results)}")

    metadata_only_ok = sum(
        1 for r in results if r.parse_depth == "metadata_only" and r.status == Status.OK
    )
    if metadata_only_ok:
        print(
            f"\n  Note: {metadata_only_ok} replay(s) only reached metadata_only depth "
            f"(no static map data available for their map_id) — their OK status reflects "
            f"only file-integrity and version checks, not game-content quality."
        )

    failed = [r for r in results if r.status == Status.FAILED]
    if failed:
        print("\nFAILURE CATEGORIES (among FAILED)")
        print(SUBSEP)
        cat_counts = Counter(r.failure_category for r in failed)
        for cat, n in cat_counts.most_common():
            print(f"  {cat.value:<32} {n}")

    degraded = [r for r in results if r.status == Status.DEGRADED]
    if degraded:
        print("\nDEGRADED REASONS (not mutually exclusive)")
        print(SUBSEP)
        reason_counts: Counter = Counter()
        for r in degraded:
            reason_counts.update(r.degraded_reasons)
        for reason, n in reason_counts.most_common():
            print(f"  {reason:<32} {n}/{len(degraded)}")

    # ── Per-replay table ──────────────────────────────────────────────────
    hdr = (
        f"{'game_id':>10}  {'player':>6}  {'status':>9}  {'patches':>7}  "
        f"{'time_scale':>10}  {'lag_into_game':>13}  "
        f"{'ingame_dur':>10}  {'span_cov%':>9}  {'cont_cov%':>9}  {'gaps':>9}  "
        f"{'days':>6}  {'ended?':>7}  {'rank_init':>9}"
    )
    print(f"\n{hdr}")
    print(SUBSEP)

    full = [r for r in results if r.parse_depth == "full"]
    ingame_durations: list[timedelta] = []
    span_coverages: list[float] = []
    cont_coverages: list[float] = []
    lags: list[timedelta] = []
    gap_counts: list[int] = []
    gap_totals: list[timedelta] = []
    ended_yes = ended_no = ended_unk = 0
    rank_yes = rank_no = rank_unk = 0

    for r in results:
        ft = strip_tz(r.seg_first_ts)
        lt = strip_tz(r.seg_last_ts)
        ingame_dur = (lt - ft) if ft and lt else None
        sog = strip_tz(r.start_of_game)
        eog = strip_tz(r.end_of_game)
        total_game_span = (eog - sog) if sog and eog else None
        span_cov_pct = (
            ingame_dur.total_seconds() / total_game_span.total_seconds() * 100
            if ingame_dur and total_game_span and total_game_span.total_seconds() > 0
            else None
        )
        cont_cov_pct = (
            r.covered_seconds / total_game_span.total_seconds() * 100
            if r.covered_seconds is not None and total_game_span and total_game_span.total_seconds() > 0
            else None
        )
        lag = (ft - sog) if ft and sog else None
        d0, d1 = r.day_first, r.day_last
        days_str = f"{d0}→{d1}" if d0 is not None and d1 is not None else "?"

        if r.parse_depth == "full":
            ended = r.game_ended
            if ended is True:
                ended_str = "YES"
                ended_yes += 1
            elif ended is False:
                ended_str = "no"
                ended_no += 1
            else:
                ended_str = "?"
                ended_unk += 1

            rank_init = r.ranking_initialized
            if rank_init is True:
                rank_init_str = "YES"
                rank_yes += 1
            elif rank_init is False:
                rank_init_str = "no"
                rank_no += 1
            else:
                rank_init_str = "?"
                rank_unk += 1

            if ingame_dur:
                ingame_durations.append(ingame_dur)
            if span_cov_pct is not None:
                span_coverages.append(span_cov_pct)
            if cont_cov_pct is not None:
                cont_coverages.append(cont_cov_pct)
            if lag is not None:
                lags.append(lag)
            if r.n_timestamps is not None:
                gap_counts.append(r.gap_count)
                gap_totals.append(r.gap_total)
        else:
            ended_str = "?"
            rank_init_str = "?"

        ts_str = f"{r.time_scale:.2f}" if r.time_scale is not None else "?"
        span_cov_str = f"{span_cov_pct:.1f}%" if span_cov_pct is not None else "?"
        cont_cov_str = f"{cont_cov_pct:.1f}%" if cont_cov_pct is not None else "?"
        gaps_str = (
            f"{r.gap_count} ({fmt_td(r.gap_total)})" if r.n_timestamps is not None else "?"
        )
        print(
            f"{(r.game_id if r.game_id is not None else '?'):>10}  "
            f"{(r.player_id if r.player_id is not None else '?'):>6}  "
            f"{r.status.value:>9}  {(r.patches or 0):>7}  "
            f"{ts_str:>10}  "
            f"{fmt_td(lag):>13}  {fmt_td(ingame_dur, unit='d'):>10}  "
            f"{span_cov_str:>9}  {cont_cov_str:>9}  {gaps_str:>9}  "
            f"{days_str:>6}  {ended_str:>7}  {rank_init_str:>9}"
        )

    print(f"\n{SEP}")
    print("SUMMARY (over fully-parsed replays only)")
    print(SEP)

    if ingame_durations:
        print("\nIn-game time span recorded (seg_last − seg_first, game-universe time):")
        print(f"  avg {fmt_td(_avg_td(ingame_durations), unit='d')}   "
              f"min {fmt_td(min(ingame_durations), unit='d')}   "
              f"max {fmt_td(max(ingame_durations), unit='d')}")

    if lags:
        print("\nLag — how far into the game recording started (game-universe time):")
        print(f"  avg {fmt_td(_avg_td(lags))}   min {fmt_td(min(lags))}   max {fmt_td(max(lags))}")

    if span_coverages:
        avg_cov = sum(span_coverages) / len(span_coverages)
        print("\nSpan coverage (recorded first→last in-game span / total game span):")
        print(f"  avg {avg_cov:.1f}%   min {min(span_coverages):.1f}%   max {max(span_coverages):.1f}%")
        print(f"  ({len(span_coverages)} replays had end_of_game; others excluded)")

    if cont_coverages:
        avg_cov = sum(cont_coverages) / len(cont_coverages)
        print(f"\nContinuity coverage (gaps > {GAP_FACTOR}x the typical sampling interval excluded):")
        print(f"  avg {avg_cov:.1f}%   min {min(cont_coverages):.1f}%   max {max(cont_coverages):.1f}%")
        print(f"  ({len(cont_coverages)} replays had end_of_game; others excluded)")

    if gap_counts:
        with_gaps = sum(1 for c in gap_counts if c > 0)
        print("\nRecording gaps:")
        print(f"  {with_gaps}/{len(gap_counts)} replays had at least one gap   "
              f"avg {sum(gap_counts) / len(gap_counts):.1f} gaps/replay   max {max(gap_counts)} gaps")
        print(f"  total gap time — avg {fmt_td(_avg_td(gap_totals), unit='d')}   "
              f"max {fmt_td(max(gap_totals), unit='d')}")

    if full:
        print("\nDid the game truly end? (game_ended flag at last recorded tick):")
        print(f"  YES: {ended_yes}   no: {ended_no}   unknown/error: {ended_unk}")

        print("\nWas the ranking initialized? (newspaper_state.ranking.initialized at last recorded tick):")
        print(f"  YES: {rank_yes}   no: {rank_no}   unknown/error: {rank_unk}")

    # ── Player validation ───────────────────────────────────────────────────
    player_counts = [r.player_count for r in full if r.player_count is not None]
    if player_counts:
        no_real_players = sum(1 for r in full if r.has_real_players is False)
        invalid_activity = sum(1 for r in full if (r.invalid_activity_state_count or 0) > 0)
        print("\nPLAYER VALIDATION")
        print(SUBSEP)
        print(f"  player count — avg {sum(player_counts) / len(player_counts):.1f}   "
              f"min {min(player_counts)}   max {max(player_counts)}")
        print(f"  replays with no real players (all AI/terrorist): {no_real_players}/{len(full)}")
        print(f"  replays with an invalid player activity_state: {invalid_activity}/{len(full)}")

    # ── Datatype version distribution ──────────────────────────────────────
    version_counter: Counter = Counter()
    for r in results:
        version_counter.update(r.required_versions)
    if version_counter:
        print("\nDATATYPE VERSION DISTRIBUTION")
        print(SUBSEP)
        for version, n in sorted(version_counter.items()):
            incompatible = any(version in r.unsupported_versions for r in results)
            flag = "  (UNSUPPORTED by this build)" if incompatible else ""
            print(f"  v{version}: {n} replay(s){flag}")

    # ── Segment count (recording-restart indicator) ─────────────────────────
    segment_counts = [r.segment_count for r in results if r.segment_count is not None]
    if segment_counts:
        multi_segment = sum(1 for c in segment_counts if c > 1)
        print("\nSEGMENT COUNT (recording restarts)")
        print(SUBSEP)
        print(f"  avg {sum(segment_counts) / len(segment_counts):.1f}   "
              f"min {min(segment_counts)}   max {max(segment_counts)}   "
              f"replays with >1 segment: {multi_segment}/{len(segment_counts)}")

    # ── Province-count consistency ───────────────────────────────────────────
    consistency = province_consistency(results)
    print(f"\n{SEP}")
    print("PROVINCE-COUNT CONSISTENCY (per map_id)")
    print(SEP)
    if consistency:
        for map_id, info in sorted(consistency.items()):
            counts = info["counts"]
            expected_str = str(info["expected_count"]) if info["expected_count"] is not None else "?"
            print(f"\nmap_id {map_id}  ({info['n_games']} replay(s))")
            print(f"  expected provinces (static map data): {expected_str}")
            print(f"  actual province count — avg {sum(counts) / len(counts):.1f}   "
                  f"min {min(counts)}   max {max(counts)}")
            if info["expected_count"] is not None:
                games_missing = sum(1 for c in counts if c < info["expected_count"])
                print(f"  replays missing at least one province: {games_missing}/{info['n_games']}")
                if info["missing_counter"]:
                    top_missing = info["missing_counter"].most_common(10)
                    missing_str = ", ".join(f"{pid} ({n}/{info['n_games']})" for pid, n in top_missing)
                    print(f"  most frequently missing province ids: {missing_str}")
                else:
                    print("  no missing provinces detected — all replays on this map have the full expected set")
    else:
        print("\nNo static map data available — province-count consistency skipped.")
    print()
