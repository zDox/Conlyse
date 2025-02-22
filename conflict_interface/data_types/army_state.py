from conflict_interface.utils import GameObject, HashMap

from dataclasses import dataclass

from .warfare import Army


@dataclass
class ArmyState(GameObject):
    STATE_ID = 6
    # TODO Implement
    """
    armies: HashMap[int, Army]
    MAPPING = {
        "armies": "armies"
    }
    """

    def update(self, new_state):
        for new_army in new_state.armies:
            if new_army.get("rm"):
                self.armies.pop(new_army.province_id)
                continue
            if new_army.province_id in self.armies.keys():
                self.armies[new_army.province_id].update(new_army)
            else:
                self.armies[new_army.province_id] = new_army
