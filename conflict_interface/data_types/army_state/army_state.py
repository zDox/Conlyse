from typing import Optional

from .army import Army

from dataclasses import dataclass

from ..custom_types import HashMap
from ..game_object import GameObject, parse_game_object
from conflict_interface.data_types.state import State


@dataclass
class ArmyState(State):
    """
    The Game State retrieved from the server.
    Holds information about the armies in the game.

    Attributes:
        STATE_TYPE (int): The unique identifier for the Army state.
        armies (HashMap[int, Army]): A mapping of army id to army object.
    """
    C = "ultshared.UltArmyState"
    STATE_TYPE = 6
    bombardments: Optional[HashMap[int, int]]  # TODO no idea if its actually int int (no examples in data1)
    change_set: bool

    armies: HashMap[int, Army]

    MAPPING = {
        "armies": "armies",
        "bombardments": "bombardments",
        "change_set": "changeSet"
    }

    def update(self, new_state):
        """
        Update the current state with the new state

        :param new_state: The new state to update with (dict)
        :return: None
        """
        if new_state is None:
            return
        for new_army in new_state.armies.values():
            if new_army.removed:
                self.armies.pop(new_army.id)
                continue
            self.armies[new_army.id] = new_army
