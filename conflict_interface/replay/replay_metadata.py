from dataclasses import dataclass
from datetime import datetime


@dataclass
class ReplayMetadata:
    version: int
    game_id: int
    player_id: int
    start_time: int
    last_time: int