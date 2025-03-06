from dataclasses import dataclass
from typing import Optional
from typing import override

from conflict_interface.data_types.game_object import GameObject
from conflict_interface.data_types.army_state.army import Army
from conflict_interface.data_types.custom_types import HashMap
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

    @override
    def update(self, other: GameObject):
        """
        Update the current state with the new state

        :param other: The new state to update with (dict)
        :return: None
        """
        if not isinstance(other, ArmyState):
            raise ValueError("UPDATE ERROR: Cannot update ArmyState with object of type: " + str(type(other)))

        if other == self:
            raise ValueError("UPDATE ERROR: Cannot update ArmyState with itself")

        if other is None:
            return
        for new_army in other.armies.values():
            if new_army.removed:
                self.armies.pop(new_army.id)
                continue
            else:
                self.armies[new_army.id] = new_army
