from conflict_interface.interface.game_interface import GameInterface


class ReplayInterface(GameInterface):
    def __init__(self, game_id: int, player_id: int):
        super().__init__(game_id=game_id)
        self.player_id = player_id