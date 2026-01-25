from dataclasses import dataclass

from conflict_interface.data_types.game_object import GameObject
from conflict_interface.data_types.game_object_binary import SerializationCategory
from conflict_interface.data_types.decorators import binary_serializable


@binary_serializable(SerializationCategory.DATACLASS)
@dataclass
class TradingProfile(GameObject):
    C = "ultshared.UltTradingProfile"
    player_id: int
    provinces_sold: int
    provinces_bought: int
    units_sold: int
    units_bought: int
    resources_sold: int
    resources_bought: int
    provinces_sold_today: int
    units_sold_today: int

    MAPPING = {
        "player_id": "playerID",
        "provinces_sold": "provincesSold",
        "provinces_bought": "provincesBought",
        "units_sold": "unitsSold",
        "units_bought": "unitsBought",
        "resources_sold": "resourcesSold",
        "resources_bought": "resourcesBought",
        "provinces_sold_today": "provincesSoldToday",
        "units_sold_today": "unitsSoldToday",
    }