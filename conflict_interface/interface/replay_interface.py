from datetime import datetime
from typing import override

from conflict_interface.data_types.game_object import parse_any
from conflict_interface.data_types.game_state.game_state import GameState
from conflict_interface.data_types.static_map_data import StaticMapData
from conflict_interface.interface.game_interface import GameInterface
from conflict_interface.replay.replay import Replay


class ReplayInterface(GameInterface):
    def __init__(self, filename: str):
        super().__init__()
        self.replay = Replay(filename, 'r')
        self.replay.__enter__()
        self.game_state = parse_any(GameState, self.replay.load_game_state(datetime.now()), self)
        self.game_state.states.map_state.map.set_static_map_data(parse_any(StaticMapData, self.replay.get_static_map_data(), self))
        self.player_id = self.replay.player_id
        self.current_time = self.replay.start_time

    @override
    def client_time(self) -> datetime:
        return self.current_time

    def set_client_time(self, time_stamp: datetime) -> None:
        self.current_time = time_stamp