"""HTML report with charts."""

import base64
import io
from collections import Counter
from pathlib import Path

from .aggregate import province_consistency
from .analyze import GAP_FACTOR
from .models import ReplayHealth, Status
from .report_text import strip_tz

_HEALTH_REPORT_CSS = """
body { font-family: -apple-system, "Segoe UI", Roboto, sans-serif; max-width: 1100px;
       margin: 2rem auto; padding: 0 1rem; color: #1f2937; line-height: 1.5; }
h1 { font-size: 1.6rem; }
h2 { margin-top: 2.5rem; border-bottom: 2px solid #e5e7eb; padding-bottom: 0.3rem; }
table { border-collapse: collapse; margin: 0.75rem 0; font-size: 0.85rem; }
th, td { border: 1px solid #e5e7eb; padding: 0.3rem 0.55rem; text-align: right; }
th { background: #f3f4f6; }
td:first-child, th:first-child { text-align: left; }
img { max-width: 100%; display: block; margin: 1rem 0; }
.metrics { display: flex; flex-wrap: wrap; gap: 1rem; margin: 1rem 0; }
.metric { background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 8px;
          padding: 0.75rem 1.25rem; min-width: 140px; }
.metric .label { font-size: 0.78rem; color: #6b7280; text-transform: uppercase; }
.metric .value { font-size: 1.4rem; font-weight: 600; }
.note { color: #6b7280; font-size: 0.88rem; }
"""


def generate_health_report(results: list[ReplayHealth], output_path: Path, top_n: int = 20) -> None:
    """Render an HTML report with charts that visualise overall replay health."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    def fig_to_base64(fig) -> str:
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=110, bbox_inches="tight")
        plt.close(fig)
        return base64.b64encode(buf.getvalue()).decode("ascii")

    def img(fig, alt: str) -> str:
        return f'<img alt="{alt}" src="data:image/png;base64,{fig_to_base64(fig)}">'

    def bar_section(title: str, counts: dict, colors: list[str]) -> str:
        labels = list(counts.keys())
        values = list(counts.values())
        fig, ax = plt.subplots(figsize=(5, 3.5))
        ax.bar(labels, values, color=colors[: len(labels)])
        ax.set_ylabel("Replays")
        ax.set_title(title)
        return f"<h2>{title}</h2>{img(fig, title.lower())}"

    def hist_section(title: str, values_label: str, values: list[float], color: str, note: str = "") -> str:
        if not values:
            return f"<h2>{title}</h2><p class='note'>No data.</p>"
        fig, ax = plt.subplots(figsize=(7, 4))
        ax.hist(values, bins=min(30, max(5, len(values) // 2)), color=color, edgecolor="white")
        ax.set_xlabel(values_label)
        ax.set_ylabel("Replays")
        ax.set_title(title)
        out = f"<h2>{title}</h2>{img(fig, title.lower())}"
        if note:
            out += f"<p class='note'>{note}</p>"
        return out

    full = [r for r in results if r.parse_depth == "full"]
    failed = [r for r in results if r.status == Status.FAILED]
    degraded = [r for r in results if r.status == Status.DEGRADED]

    rows = []
    for r in full:
        sog = strip_tz(r.start_of_game)
        eog = strip_tz(r.end_of_game)
        ft = strip_tz(r.seg_first_ts)
        lt = strip_tz(r.seg_last_ts)
        total_game_span = (eog - sog) if sog and eog else None
        cont_cov_pct = (
            r.covered_seconds / total_game_span.total_seconds() * 100
            if r.covered_seconds is not None and total_game_span and total_game_span.total_seconds() > 0
            else None
        )
        span_cov_pct = (
            (lt - ft).total_seconds() / total_game_span.total_seconds() * 100
            if ft and lt and total_game_span and total_game_span.total_seconds() > 0
            else None
        )
        rows.append({
            "label": f"{r.game_id}/{r.player_id}",
            "typical_interval": r.typical_interval,
            "gap_count": r.gap_count,
            "gap_total": r.gap_total,
            "gaps": r.gaps,
            "sog": sog,
            "eog": eog,
            "cont_cov_pct": cont_cov_pct,
            "span_cov_pct": span_cov_pct,
            "ingame_dur": (lt - ft) if ft and lt else None,
            "lag": (ft - sog) if ft and sog else None,
            "time_scale": r.time_scale,
            "game_ended": r.game_ended,
            "ranking_initialized": r.ranking_initialized,
            "player_count": r.player_count,
        })

    with_intervals = [x for x in rows if x["typical_interval"] is not None]
    with_gaps = [x for x in rows if x["gap_count"] > 0]
    all_gap_durations_min = [gap[2] / 60.0 for x in rows for gap in x["gaps"]]
    cont_coverages = [x["cont_cov_pct"] for x in rows if x["cont_cov_pct"] is not None]
    span_coverages = [x["span_cov_pct"] for x in rows if x["span_cov_pct"] is not None]
    ended_yes = sum(1 for x in rows if x["game_ended"] is True)
    ended_no = sum(1 for x in rows if x["game_ended"] is False)
    ended_unk = sum(1 for x in rows if x["game_ended"] is None)
    rank_yes = sum(1 for x in rows if x["ranking_initialized"] is True)
    rank_no = sum(1 for x in rows if x["ranking_initialized"] is False)
    rank_unk = sum(1 for x in rows if x["ranking_initialized"] is None)

    sections: list[str] = []

    # 1. Overall status breakdown
    status_counts = Counter(r.status for r in results)
    sections.append(bar_section(
        "Overall status",
        {s.value: status_counts.get(s, 0) for s in (Status.OK, Status.DEGRADED, Status.FAILED)},
        ["#16a34a", "#f59e0b", "#dc2626"],
    ))

    # 2. Failure category breakdown
    if failed:
        cat_counts = Counter(r.failure_category.value for r in failed)
        fig, ax = plt.subplots(figsize=(7, max(3, 0.4 * len(cat_counts))))
        labels = list(cat_counts.keys())
        values = list(cat_counts.values())
        ax.barh(labels, values, color="#dc2626")
        ax.set_xlabel("Replays")
        ax.set_title("Failure categories")
        sections.append(f"<h2>Failure categories</h2>{img(fig, 'failure categories')}")

    # 3. Degraded-reason breakdown
    if degraded:
        reason_counts: Counter = Counter()
        for r in degraded:
            reason_counts.update(r.degraded_reasons)
        fig, ax = plt.subplots(figsize=(7, max(3, 0.4 * len(reason_counts))))
        labels = list(reason_counts.keys())
        values = list(reason_counts.values())
        ax.barh(labels, values, color="#f59e0b")
        ax.set_xlabel("Replays")
        ax.set_title("Degraded reasons (not mutually exclusive)")
        sections.append(f"<h2>Degraded reasons</h2>{img(fig, 'degraded reasons')}")

    # 4. Coverage distribution (continuity vs span coverage, overlaid)
    if cont_coverages or span_coverages:
        fig, ax = plt.subplots(figsize=(7, 4))
        bins = np.linspace(
            min(cont_coverages + span_coverages, default=0),
            max(cont_coverages + span_coverages, default=100),
            30,
        )
        if span_coverages:
            ax.hist(span_coverages, bins=bins, color="#2563eb", alpha=0.5, edgecolor="white", label="span coverage")
        if cont_coverages:
            ax.hist(cont_coverages, bins=bins, color="#dc2626", alpha=0.5, edgecolor="white", label="continuity coverage")
        ax.set_xlabel("Coverage of total game span (%)")
        ax.set_ylabel("Replays")
        ax.set_title("Distribution of coverage across replays")
        ax.legend(loc="upper left")
        note = ""
        if span_coverages:
            note += (
                f"span_cov% — avg {np.mean(span_coverages):.1f}% &nbsp;"
                f"median {np.median(span_coverages):.1f}% &nbsp;"
                f"min {np.min(span_coverages):.1f}% &nbsp;"
                f"max {np.max(span_coverages):.1f}%<br>"
            )
        if cont_coverages:
            note += (
                f"cont_cov% — avg {np.mean(cont_coverages):.1f}% &nbsp;"
                f"median {np.median(cont_coverages):.1f}% &nbsp;"
                f"min {np.min(cont_coverages):.1f}% &nbsp;"
                f"max {np.max(cont_coverages):.1f}%"
            )
        sections.append(
            f"<h2>Coverage distribution</h2>{img(fig, 'coverage distribution histogram')}"
            f"<p class='note'>{note}</p>"
        )

    # 5. Span coverage vs continuity coverage
    span_vs_cont = [
        (x["span_cov_pct"], x["cont_cov_pct"]) for x in rows
        if x["span_cov_pct"] is not None and x["cont_cov_pct"] is not None
    ]
    if span_vs_cont:
        xs, ys = zip(*span_vs_cont)
        fig, ax = plt.subplots(figsize=(6, 6))
        ax.scatter(xs, ys, alpha=0.6, color="#2563eb")
        lim = (0, 105)
        ax.plot(lim, lim, "--", color="#9ca3af", label="span_cov% = cont_cov%")
        ax.set_xlim(lim)
        ax.set_ylim(lim)
        ax.set_xlabel("span_cov%  (first→last span / total game span)")
        ax.set_ylabel("cont_cov%  (gap-aware continuity coverage)")
        ax.set_title("Continuity coverage vs. span coverage")
        ax.legend(loc="lower right")
        sections.append(
            f"<h2>Coverage — how much of each game was actually recorded</h2>"
            f"{img(fig, 'span vs continuity coverage scatter')}"
        )

    # 6. In-game time span recorded
    sections.append(hist_section(
        "In-game time span recorded",
        "In-game span recorded (days, seg_last − seg_first, game-universe time)",
        [x["ingame_dur"].total_seconds() / 86400.0 for x in rows if x["ingame_dur"] is not None],
        "#16a34a",
    ))

    # 7. Recording lag
    sections.append(hist_section(
        "Recording lag",
        "Lag before recording started (hours, game-universe time)",
        [x["lag"].total_seconds() / 3600.0 for x in rows if x["lag"] is not None],
        "#f59e0b",
    ))

    # 8. Game end-state
    fig, ax = plt.subplots(figsize=(5, 3.5))
    ax.bar(["YES", "no", "unknown"], [ended_yes, ended_no, ended_unk], color=["#16a34a", "#dc2626", "#9ca3af"])
    ax.set_ylabel("Replays")
    ax.set_title("Did the game truly end? (game_ended at last recorded tick)")
    sections.append(f"<h2>Game end-state</h2>{img(fig, 'game ended breakdown')}")

    # 9. Ranking initialization
    fig, ax = plt.subplots(figsize=(5, 3.5))
    ax.bar(["YES", "no", "unknown"], [rank_yes, rank_no, rank_unk], color=["#16a34a", "#dc2626", "#9ca3af"])
    ax.set_ylabel("Replays")
    ax.set_title("Was the ranking initialized? (newspaper_state.ranking.initialized)")
    sections.append(f"<h2>Ranking initialization</h2>{img(fig, 'ranking initialized breakdown')}")

    # 10. Player-count distribution
    sections.append(hist_section(
        "Player-count distribution",
        "Players present at last recorded tick",
        [x["player_count"] for x in rows if x["player_count"] is not None],
        "#8b5cf6",
    ))

    # 11. Time-scale distribution
    sections.append(hist_section(
        "Time-scale distribution",
        "Game time scale (in-game time per real-world time)",
        [x["time_scale"] for x in rows if x["time_scale"] is not None],
        "#0891b2",
    ))

    # 12. Typical sampling interval distribution
    if with_intervals:
        intervals_min = [x["typical_interval"].total_seconds() / 60.0 for x in with_intervals]
        fig, ax = plt.subplots(figsize=(7, 4))
        ax.hist(intervals_min, bins=min(30, max(5, len(intervals_min) // 2)), color="#2563eb", edgecolor="white")
        ax.set_xlabel("Typical sampling interval (minutes, median Δ between recorded ticks)")
        ax.set_ylabel("Replays")
        ax.set_title("Distribution of typical sampling interval across replays")
        sections.append(f"<h2>Typical sampling interval</h2>{img(fig, 'typical interval histogram')}")

    # 13. Gap duration distribution (log-scale)
    if all_gap_durations_min:
        fig, ax = plt.subplots(figsize=(7, 4))
        positive = [d for d in all_gap_durations_min if d > 0]
        bins = np.logspace(np.log10(min(positive)), np.log10(max(positive)), 30)
        ax.hist(positive, bins=bins, color="#dc2626", edgecolor="white")
        ax.set_xscale("log")
        ax.set_xlabel("Gap duration (minutes, log scale)")
        ax.set_ylabel("Gaps")
        ax.set_title(f"Distribution of individual gap durations (>{GAP_FACTOR}× the typical interval)")
        sections.append(f"<h2>Gap duration distribution</h2>{img(fig, 'gap duration histogram')}")
    else:
        sections.append("<h2>Gap duration distribution</h2><p class='note'>No gaps detected in any replay.</p>")

    # 14. Gap count / total time per replay (top N) + timeline
    if with_gaps:
        top_by_count = sorted(with_gaps, key=lambda x: x["gap_count"], reverse=True)[:top_n]
        fig, ax = plt.subplots(figsize=(7, max(3, 0.32 * len(top_by_count))))
        labels = [x["label"] for x in reversed(top_by_count)]
        values = [x["gap_count"] for x in reversed(top_by_count)]
        ax.barh(labels, values, color="#f59e0b")
        ax.set_xlabel("Number of detected gaps")
        ax.set_title(f"Top {len(top_by_count)} replays by gap count (game_id/player_id)")
        sections.append(f"<h2>Replays with the most gaps</h2>{img(fig, 'gap count per replay')}")

        top_by_total = sorted(with_gaps, key=lambda x: x["gap_total"], reverse=True)[:top_n]
        fig, ax = plt.subplots(figsize=(7, max(3, 0.32 * len(top_by_total))))
        labels = [x["label"] for x in reversed(top_by_total)]
        values = [x["gap_total"].total_seconds() / 3600.0 for x in reversed(top_by_total)]
        ax.barh(labels, values, color="#8b5cf6")
        ax.set_xlabel("Total gap time (hours)")
        ax.set_title(f"Top {len(top_by_total)} replays by total missing time (game_id/player_id)")
        sections.append(f"<h2>Replays with the most missing time</h2>{img(fig, 'total gap time per replay')}")

        timeline_candidates = [x for x in with_gaps if x["sog"] and x["eog"]]
        timeline_rows = sorted(timeline_candidates, key=lambda x: x["gap_total"], reverse=True)[:top_n]
        if timeline_rows:
            fig, ax = plt.subplots(figsize=(9, max(3, 0.4 * len(timeline_rows))))
            for i, x in enumerate(reversed(timeline_rows)):
                sog, eog = x["sog"], x["eog"]
                span_h = (eog - sog).total_seconds() / 3600.0
                ax.barh(i, span_h, left=0, color="#bbf7d0", edgecolor="#16a34a", height=0.6, label="recorded span" if i == 0 else None)
                for gap_start, gap_end, _ in x["gaps"]:
                    g0 = (strip_tz(gap_start) - sog).total_seconds() / 3600.0
                    g1 = (strip_tz(gap_end) - sog).total_seconds() / 3600.0
                    ax.barh(i, g1 - g0, left=g0, color="#dc2626", height=0.6, label="gap" if i == 0 else None)
            ax.set_yticks(range(len(timeline_rows)))
            ax.set_yticklabels([x["label"] for x in reversed(timeline_rows)])
            ax.set_xlabel("Hours since start_of_game")
            ax.set_title(f"Gap timeline — top {len(timeline_rows)} replays by total missing time")
            ax.legend(loc="upper right")
            sections.append(
                f"<h2>Where the gaps fall within each game</h2>"
                f"<p class='note'>Green = total game span; red = detected recording gaps.</p>"
                f"{img(fig, 'gap timeline gantt chart')}"
            )

    # 15. Datatype version distribution
    version_counter: Counter = Counter()
    incompatible_versions: set[int] = set()
    for r in results:
        version_counter.update(r.required_versions)
        incompatible_versions.update(r.unsupported_versions)
    if version_counter:
        fig, ax = plt.subplots(figsize=(6, 3.5))
        labels = [f"v{v}" for v in sorted(version_counter)]
        values = [version_counter[v] for v in sorted(version_counter)]
        colors = ["#dc2626" if v in incompatible_versions else "#2563eb" for v in sorted(version_counter)]
        ax.bar(labels, values, color=colors)
        ax.set_ylabel("Replays")
        ax.set_title("Datatype version distribution (red = unsupported by this build)")
        sections.append(f"<h2>Datatype versions</h2>{img(fig, 'datatype version distribution')}")

    # 16. Province-count consistency
    consistency = province_consistency(results)
    if consistency:
        table_rows = []
        for map_id, info in sorted(consistency.items()):
            counts = info["counts"]
            expected_str = str(info["expected_count"]) if info["expected_count"] is not None else "?"
            avg_c = sum(counts) / len(counts)
            missing_replays = (
                sum(1 for c in counts if c < info["expected_count"])
                if info["expected_count"] is not None else "?"
            )
            table_rows.append(
                f"<tr><td>{map_id}</td><td>{info['n_games']}</td><td>{expected_str}</td>"
                f"<td>{avg_c:.1f}</td><td>{min(counts)}</td><td>{max(counts)}</td>"
                f"<td>{missing_replays}</td></tr>"
            )
        table_html = (
            "<table><tr><th>map_id</th><th>replays</th><th>expected provinces</th>"
            "<th>avg actual</th><th>min</th><th>max</th><th>replays missing ≥1 province</th></tr>"
            + "".join(table_rows) + "</table>"
        )
        sections.append(f"<h2>Province-count consistency (per map)</h2>{table_html}")

        global_missing: Counter = Counter()
        for info in consistency.values():
            global_missing.update(info["missing_counter"])
        if global_missing:
            top_missing = global_missing.most_common(top_n)
            fig, ax = plt.subplots(figsize=(7, max(3, 0.32 * len(top_missing))))
            labels = [str(pid) for pid, _ in reversed(top_missing)]
            values = [n for _, n in reversed(top_missing)]
            ax.barh(labels, values, color="#dc2626")
            ax.set_xlabel("Number of replays missing this province")
            ax.set_title(f"Top {len(top_missing)} most frequently missing provinces (province id)")
            sections.append(f"<h2>Most frequently missing provinces</h2>{img(fig, 'missing provinces per replay')}")
    else:
        sections.append(
            "<h2>Province-count consistency</h2>"
            "<p class='note'>No static map data provided — skipped.</p>"
        )

    n_with_gaps = len(with_gaps)
    avg_span_cov = sum(span_coverages) / len(span_coverages) if span_coverages else None
    avg_cont_cov = sum(cont_coverages) / len(cont_coverages) if cont_coverages else None
    metrics_html = (
        "<div class='metrics'>"
        f"<div class='metric'><div class='label'>Replays analysed</div><div class='value'>{len(results)}</div></div>"
        f"<div class='metric'><div class='label'>OK</div><div class='value'>{status_counts.get(Status.OK, 0)}</div></div>"
        f"<div class='metric'><div class='label'>Degraded</div><div class='value'>{status_counts.get(Status.DEGRADED, 0)}</div></div>"
        f"<div class='metric'><div class='label'>Failed</div><div class='value'>{status_counts.get(Status.FAILED, 0)}</div></div>"
        f"<div class='metric'><div class='label'>Avg span coverage</div><div class='value'>"
        f"{f'{avg_span_cov:.1f}%' if avg_span_cov is not None else '?'}</div></div>"
        f"<div class='metric'><div class='label'>Avg continuity coverage</div><div class='value'>"
        f"{f'{avg_cont_cov:.1f}%' if avg_cont_cov is not None else '?'}</div></div>"
        f"<div class='metric'><div class='label'>Replays with gaps</div><div class='value'>{n_with_gaps}/{len(full) or 1}</div></div>"
        "</div>"
    )

    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Replay health report</title>
<style>{_HEALTH_REPORT_CSS}</style>
</head>
<body>
<h1>Replay health report</h1>
<p class="note">
An overview of the health of {len(results)} replays: overall status (OK/degraded/failed),
why replays failed or were degraded, how much of each game was actually captured (span vs.
gap-aware continuity coverage), player and ranking validity, and province-count consistency
against static map data. A "gap" is a delta between two consecutive recorded in-game
timestamps that is more than {GAP_FACTOR}× the replay's own typical (median) sampling
interval — i.e. a point where recording silently paused and resumed later.
</p>
{metrics_html}
{''.join(sections)}
</body>
</html>
"""

    output_path.write_text(html, encoding="utf-8")
    print(f"\nReplay health report written to {output_path}", flush=True)
