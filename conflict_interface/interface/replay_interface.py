from datetime import UTC
from datetime import datetime
from datetime import timedelta
from pprint import pprint
from time import time
from typing import override

from conflict_interface.data_types.game_object import parse_any
from conflict_interface.data_types.game_state.game_state import GameState
from conflict_interface.data_types.static_map_data import StaticMapData
from conflict_interface.interface.game_interface import GameInterface
from conflict_interface.logger_config import get_logger
from conflict_interface.replay.apply_replay import apply_patch_any
from conflict_interface.replay.replay import Replay

logger = get_logger()

class ReplayInterface(GameInterface):
    def __init__(self, filename: str):
        super().__init__()
        self.replay = Replay(filename, 'r')
        self.game_state: GameState | None = None
        self.static_map_data = None
        self.player_id: int | None = None
        self.current_time: datetime | None = None
        self.game_id: int | None = None

    def open(self):
        t1 = time()
        self.replay.open()
        logger.debug(f"Loading Game State from disk took {time() - t1} seconds")
        t2 = time()
        self.game_state = parse_any(GameState, self.replay.get_initial_game_state(), self)
        logger.debug(f"GameState parse took {time() - t2} seconds")
        t3 = time()
        self.static_map_data = parse_any(StaticMapData, self.replay.get_static_map_data(), self)
        self.game_state.states.map_state.map.set_static_map_data(self.static_map_data)
        self._update_player_id()
        self.game_id = self.replay.game_id
        self.current_time = self.replay.start_time
        logger.debug(f"Loading and setting static map data took {time() - t3} seconds")

    def close(self):
        self.replay.close()

    def _find_current_player_id(self) -> int | None:
        for player in self.get_players().values():
            if player.activity_state == "ACTIVE" or player.activity_state == "UNKNOWN":
                return player.player_id

    def _update_player_id(self):
        if self.player_id is not None and (self.get_player(self.player_id).activity_state == "ACTIVE"
            or self.get_player(self.player_id).activity_state == "UNKNOWN"):
            return

        self.player_id = self._find_current_player_id()

        if self.player_id is None:
            raise Exception("Could not determine player ID")


    @override
    def client_time(self) -> datetime:
        return self.current_time

    @property
    def start_time(self) -> datetime:
        return self.replay.start_time

    @property
    def end_time(self) -> datetime:
        return self.replay.last_time

    def set_client_time(self, time_stamp: datetime) -> None:
        if self.current_time == time_stamp:
            return
        if time_stamp < self.replay.start_time == self.current_time:
            return

        if time_stamp < self.replay.start_time:
            self.game_state = parse_any(GameState, self.replay.get_initial_game_state(), self)
            return

        patches = self.replay.jump_from_to(self.current_time, time_stamp)
        for rp in patches:
            apply_patch_any(rp, GameState, self.game_state, self)

        self.current_time = time_stamp
        self.game_state.states.map_state.map.set_static_map_data(self.static_map_data)
        self._update_player_id()

    def get_timestamps(self) -> list[datetime]:
        return [datetime.fromtimestamp(ts / 1000, tz=UTC) for ts in self.replay.get_timestamps()]

    def average_update_frequency(self) -> timedelta:
        """
        Computes the average update frequency as a timedelta.
        """
        timestamps = self.get_timestamps()
        if len(timestamps) < 2:  # Need at least 2 timestamps to calculate frequency
            return timedelta(0)

        total_time = (self.end_time - self.end_time).total_seconds()
        num_intervals = len(timestamps) - 1

        return timedelta(seconds=num_intervals / total_time if total_time > 0 else 0.0)
