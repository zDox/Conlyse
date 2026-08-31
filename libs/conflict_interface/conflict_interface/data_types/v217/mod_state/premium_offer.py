from dataclasses import dataclass
from typing import Optional

from ..custom_types import DateTimeSecondsInt
from ..custom_types import HashMap
from ..custom_types import TimeDeltaMillisecondsInt
from conflict_interface.game_object.game_object import GameObject
from conflict_interface.game_object.game_object_binary import SerializationCategory
from conflict_interface.game_object.decorators import conflict_serializable
from ..mod_state.premium import Premium

from ..version import VERSION
@conflict_serializable(SerializationCategory.DATACLASS, version = VERSION)
@dataclass
class PremiumOffer(GameObject):
    C = "po"
    id: int
    premiums: Optional[HashMap[int, Premium]]
    currency: Optional[str]
    start_date: Optional[DateTimeSecondsInt] # !TODO Check Type
    end_date: Optional[DateTimeSecondsInt] # !TODO Check Type
    country: Optional[str]
    price_function: HashMap[int, float]
    price_items: Optional[list[int]] # !TODO Check Type

    featured: int = 0
    duration: TimeDeltaMillisecondsInt = 0
    offer_category: int = 2
    price: float = 1000.0
    price_step: int = 0
    min_price: int = 0
    amount: int = 1
    quantity: int = 0

    MAPPING = {
        "id" : "id",
        "premiums" : "pm",
        "currency": "c",
        "start_date": "sd",
        "end_date": "ed",
        "featured": "f",
        "country": "co",
        "price_function": "pf",
        "price_items": "priceItems",
        "duration": "d",
        "offer_category": "oc",
        "price": "pr",
        "price_step": "ps",
        "min_price": "mp",
        "amount": "a",
        "quantity": "q",
    }




