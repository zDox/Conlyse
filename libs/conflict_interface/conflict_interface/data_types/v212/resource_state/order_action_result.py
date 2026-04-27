from enum import Enum

from conflict_interface.game_object.game_object_binary import SerializationCategory
from conflict_interface.game_object.decorators import conflict_serializable


from ..version import VERSION
@conflict_serializable(SerializationCategory.ENUM, version = VERSION)
class OrderActionResult(Enum):
    OK = 0
    ORDER_NOT_FOUND = 1
    NOT_BUYABLE_ORDER = 2
    NOT_SELLABLE_ORDER = 3
    CANT_CANCEL_FOREIGN_ORDER = 4
    PRICE_TO_HIGH = 5
    PRICE_TO_LOW = 6
    AMOUNT_TO_LOW = 7
    AMOUNT_TO_HIGH = 8
    RESOURCE_ENTRY_MISSING = 9
    NOT_ENOUGH_MONEY = 10
