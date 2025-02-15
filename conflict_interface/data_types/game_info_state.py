from conflict_interface.utils import GameObject

from dataclasses import dataclass

from .game_info import GameInfo

@dataclass
class GameInfoState(GameObject):
    STATE_ID = 12
    game_info: GameInfo
    MAPPING = {"game_info": "gameInfo"}