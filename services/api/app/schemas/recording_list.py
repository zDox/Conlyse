from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class RecordingListAddRequest(BaseModel):
    game_id: int = Field(..., ge=1)


class RecordingListItem(BaseModel):
    game_id: int
    scenario_id: int
    created_at: datetime

