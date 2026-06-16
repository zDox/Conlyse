"""
Fixed real-time resampling grid for the temporal Transformer.

`T_STEPS` snapshots spaced `STEP_DAYS` apart, right-aligned so the last step
(index `T_STEPS - 1`) always lands exactly on "now" (`day_of_game`) — this is the
position the temporal Transformer reads its output from. Earlier steps count
backwards from "now"; steps that land before day 0 (short games) are left-padded
and marked invalid via `time_mask`. Cold start (`day_of_game == 0`) yields exactly
one valid step (the last one).

`NUM_ANCHORS` / `build_anchor_days` define the deterministic "now" anchors used by
`gnn-extract` to turn one finished replay into `NUM_ANCHORS` training samples: evenly
spaced mid-game days, so the model learns to predict the (fixed, game-final) outcome
from states where it is not yet decided — instead of from the game-ending state
itself (which would leak the outcome, since the target is derived from that same
state).
"""

from __future__ import annotations

from dataclasses import dataclass

T_STEPS = 20
STEP_DAYS = 1
WINDOW_DAYS = (T_STEPS - 1) * STEP_DAYS

NUM_ANCHORS = 10


@dataclass
class ResampleStep:
    index: int
    target_day: float
    valid: bool


def build_resampling_schedule(
    day_of_game: float, t_steps: int = T_STEPS, step_days: int = STEP_DAYS
) -> list[ResampleStep]:
    """Right-aligned schedule: step `t_steps - 1` always lands on `day_of_game`."""
    schedule = []
    for i in range(t_steps):
        target_day = day_of_game - (t_steps - 1 - i) * step_days
        valid = target_day >= 0.0
        schedule.append(ResampleStep(index=i, target_day=max(0.0, target_day), valid=valid))
    return schedule


def build_anchor_days(day_of_game_end: float, num_anchors: int = NUM_ANCHORS) -> list[int]:
    """`num_anchors` deterministic, evenly-spaced mid-game anchor days for one replay.

    Anchors sit at the midpoints of `num_anchors` equal slices of
    `[0, day_of_game_end]`, so (for typical game lengths) none lands exactly on day 0
    (cold start) or on `day_of_game_end` (the game-ending state used to compute the
    target — including it as an anchor would leak the outcome into the input).
    """
    return [round(day_of_game_end * (i + 0.5) / num_anchors) for i in range(num_anchors)]
