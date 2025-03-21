from dataclasses import dataclass
from dataclasses import field
from typing import Optional
from typing import override

from conflict_interface.data_types.game_object import GameObject
from conflict_interface.data_types.army_state.army import Army
from conflict_interface.data_types.custom_types import HashMap
from conflict_interface.data_types.state import State
from conflict_interface.replay.replay_patch import BidirectionalReplayPatch
from conflict_interface.replay.replay_patch import PathNode
from conflict_interface.replay.replay_patch import ReplayPatch


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
    bombardments: Optional[HashMap[int, int]] = field(default_factory=dict) # TODO no idea if its actually int int (no examples in data1)
    change_set: bool = False

    armies: HashMap[int, Army] = field(default_factory=dict)

    MAPPING = {
        "armies": "armies",
        "bombardments": "bombardments",
        "change_set": "changeSet"
    }

    def update(self, other: GameObject, path: list[PathNode] = None, rp: BidirectionalReplayPatch = None):
        """
        Update the current state with the new state

        :param other: The new state to update with (dict)
        :return: None
        """
        if not isinstance(other, ArmyState):
            raise ValueError("UPDATE ERROR: Cannot update ArmyState with object of type: " + str(type(other)))

        if other == self:
            raise ValueError("UPDATE ERROR: Cannot update ArmyState with itself")
        super().update(other, path=path, rp=rp)


        # Merging two armies
        for new_army in other.armies.values():
            if new_army.removed and new_army.id in self.armies:
                if rp:
                    rp.remove(path + ["armies", new_army.id], self.armies.get(new_army.id))
                self.armies.pop(new_army.id)
                continue
            else:
                if rp:
                    old_army = self.armies[new_army.id]
                    for attr in new_army.get_mapping():
                        if getattr(old_army, attr) != getattr(new_army, attr):
                             rp.replace(path + ["armies", new_army.id, attr],
                                        getattr(old_army, attr),
                                        getattr(new_army, attr))
                self.armies[new_army.id] = new_army