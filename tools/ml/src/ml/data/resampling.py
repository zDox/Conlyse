"""
Fixed real-time resampling grid for the temporal Transformer.

`T_STEPS` snapshots spaced `STEP_DAYS` apart, right-aligned so the last step
(index `T_STEPS - 1`) always lands exactly on "now" (`day_of_game`) — this is the
position the temporal Transformer reads its output from. Earlier steps count
backwards from "now"; steps that land before day 0 (short games) are left-padded
and marked invalid via `time_mask`. Cold start (`day_of_game == 0`) yields exactly
one valid step (the last one).
"""
from __future__ import annotations

from dataclasses import dataclass

T_STEPS = 20
STEP_DAYS = 3
WINDOW_DAYS = (T_STEPS - 1) * STEP_DAYS


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
