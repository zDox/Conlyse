from dataclasses import dataclass

from .upgrades import UpgradeType


@dataclass
class ModState:
    STATE_ID = 11
    upgrades: dict[int, UpgradeType]
    # unit_types: list(UnitType)
    # research_types: list(ResearchType)

    @classmethod
    def from_dict(cls, obj):
        upgrades = {int(upgrade_id): UpgradeType.from_dict(upgrade)
                    for upgrade_id, upgrade
                    in list(obj["upgrades"].items())[1:]}
        return cls(**{
            "upgrades": upgrades,
            })
