from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from conflict_interface.data_types.resource_state.resource_types import ResourceType
from conflict_interface.data_types.custom_types import AskListInner
from conflict_interface.data_types.custom_types import AskListOuter
from conflict_interface.data_types.custom_types import BidListInner
from conflict_interface.data_types.custom_types import BidListOuter
from conflict_interface.data_types.custom_types import HashMap
from conflict_interface.data_types.resource_state.order import Order
from conflict_interface.data_types.resource_state.resource_profile import ResourceProfile
from conflict_interface.data_types.resource_state.trading import Trading
from conflict_interface.data_types.resource_state.traiding_action import OrderAction
from conflict_interface.data_types.state import State
from conflict_interface.logger_config import get_logger

logger = get_logger()

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

@dataclass
class ResourceState(State):
    C = "ultshared.UltResourceState"
    STATE_TYPE = 4
    resource_profiles: HashMap[int, ResourceProfile]

    trading: Trading
    bids: BidListOuter[BidListInner[Order]]
    asks: AskListOuter[AskListInner[Order]]
    prices: list[float] # Has to be floats



    MAPPING = {
        "resource_profiles": "resourceProfs",
        "trading": "trading",
        "bids": "bids",
        "asks": "asks",
        "prices": "prices",
    }
    def get_order(self, buy: bool , resource_type: ResourceType = -1, piece_price: float = -1, amount: int = -1, order_id: int = -1):
        for inner in self.bids if buy else self.asks:
            for order in inner:
                if order.order_id == order_id or (order.resource_type == resource_type and order.limit == piece_price and order.amount == amount):
                    return order

        logger.warning(f"Order not found for resource_type: {resource_type}, piece_price: {piece_price}, amount: {amount}, buy: {buy}")
        return None

    def cancel_order(self, order: Order):
        if order is None:
            return None, OrderActionResult.ORDER_NOT_FOUND

        action = OrderAction(order = order, cancel=True)
        return self.game.do_action(action), OrderActionResult.OK

    def create_ask(self, resource_type: ResourceType, piece_price: float, amount: int): # Offer to Sell resource to anyone
        resource_enty = self.game.get_resource_entry(resource_type)
        if resource_enty is None:
            return None, OrderActionResult.RESOURCE_ENTRY_MISSING

        if piece_price > resource_enty.max_price:
            return None, OrderActionResult.PRICE_TO_HIGH
        elif piece_price < resource_enty.min_price:
            return None, OrderActionResult.PRICE_TO_LOW

        if amount < 1:
            return None, OrderActionResult.AMOUNT_TO_LOW
        if amount > resource_enty.get_resource_amount():
            return None, OrderActionResult.AMOUNT_TO_HIGH

        order = Order(
            buy=False,
            amount=amount,
            limit= piece_price,
            resource_type= resource_type,
            player_id= self.game.player_id,
            embargo = False,

            total_price = None,
            icon = None,
            icon_small = None,
            order_id = None,
            is_owner = None
        )
        action = OrderAction(order = order, cancel=False)
        return self.game.do_action(action), OrderActionResult.OK

    def create_bid(self, resource_type: ResourceType, piece_price: float, amount: int): # Ask to Buy resource from anyone
        resource_entry = self.game.get_resource_entry(resource_type)
        money_entry = self.game.get_resource_entry(ResourceType.MONEY)
        if resource_entry is None:
            return None, OrderActionResult.RESOURCE_ENTRY_MISSING

        if amount*piece_price > money_entry.get_resource_amount():
            return None, OrderActionResult.AMOUNT_TO_HIGH

        order = Order(
            buy=True,
            amount=amount,
            limit= piece_price,
            resource_type= resource_type,
            player_id= self.game.player_id,
            embargo = False,

            total_price = None,
            icon = None,
            icon_small = None,
            order_id = None,
            is_owner = None
        )

        action = OrderAction(order = order, cancel=False)
        return self.game.do_action(action), OrderActionResult.OK