from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class GameItem(BaseModel):
    game_id: int
    scenario_id: int
    status: str
    discovered_date: datetime
    started_date: datetime | None
    completed_date: datetime | None

