from .army import Army


from dataclasses import dataclass

from ..custom_types import HashMap
from ..game_object import GameObject


@dataclass
class ArmyState(GameObject):
    """
    The Game State retrieved from the server.
    Holds information about the armies in the game.

    Attributes:
        STATE_ID (int): The unique identifier for the Army state.
        armies (HashMap[int, Army]): A mapping of army id to army object.
    """
    C = "ultshared.UltArmyState"
    STATE_ID = 6

    armies: HashMap[int,Army]

    MAPPING = {"armies": "armies"}


    def update(self, new_state):
        """
        Update the current state with the new state

        :param new_state: The new state to update with (dict)
        :return: None
        """

        new_state = self.from_dict(new_state)
        for new_army in new_state.armies:
            if new_army.removed:
                self.armies.pop(new_army.id)
                continue
            self.armies[new_army.id] = new_army






