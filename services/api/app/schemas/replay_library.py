from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class ReplayLibraryAddRequest(BaseModel):
    game_id: int = Field(..., ge=1)


class ReplayLibraryItem(BaseModel):
    game_id: int
    scenario_id: int
    created_at: datetime

