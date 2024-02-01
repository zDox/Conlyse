from dataclasses import dataclass

from .warfare import Army


@dataclass
class ArmyState:
    STATE_ID = 6
    armies: dict[int, Army]

    @classmethod
    def from_dict(cls, obj):
        armies = {army["id"]: Army.from_dict(army)
                  for army in list(obj["armies"].values())[1:]
                  if not army.get("rm")}
        return cls(**{
            "armies": armies,
            })

    def update(self, new_state):
        for new_army in new_state.armies:
            if new_army.get("rm"):
                self.armies.pop(new_army.id)
                continue
            if new_army.id in self.armies.keys():
                self.armies[new_army.id].update(new_army)
            else:
                self.armies[new_army.id] = new_army
