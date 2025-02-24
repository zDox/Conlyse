from conflict_interface.utils import GameObject, HashMap

from dataclasses import dataclass

from army import Army


@dataclass
class ArmyState(GameObject):
    STATE_ID = 6

    armies: HashMap[Army]

    MAPPING = {"armies": "armies"}
    

    def update(self, new_state):
        for new_army in new_state.armies:
            if new_army.removed:
                self.armies.pop(new_army.id)
                continue
            self.armies[new_army.id] = new_army






