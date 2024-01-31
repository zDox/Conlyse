from dataclasses import dataclass

import GameInfo


@dataclass
class GameInfoState:
    STATE_ID = 12
    game_info: GameInfo

    @classmethod
    def from_dict(cls, obj):
        return cls(**{
            "game_info": GameInfo.from_dict(obj)
            })
