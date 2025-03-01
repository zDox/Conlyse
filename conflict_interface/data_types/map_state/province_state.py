from dataclasses import dataclass

from conflict_interface.data_types.custom_types import HashMap
from conflict_interface.data_types.game_object import GameObject


@dataclass
class ProvinceState(GameObject):
    C = "ultshared.map.UltProvinceState"

    id: int
    features: HashMap[int, str] # TODO value could be an enum
    visibilities: HashMap[str, int] # TODO key could be an enum
    name: str
    production_factor: float
    consumption_factor: float
    max_morale: int # TODO: maby float?
    key: str # TODO could be an enum

    MAPPING = {
        "id": "id",
        "features": "features",
        "visibilities": "visibilities",
        "name": "name",
        "production_factor": "productionFactor",
        "consumption_factor": "consumptionFactor",
        "max_morale": "maxMorale",
        "key": "key"
    }