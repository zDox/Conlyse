from dataclasses import dataclass
from typing import Optional
from conflict_interface.data_types.resource_state.order_action_result import OrderActionResult

from conflict_interface.data_types.resource_state.resource_state_enums import ResourceType
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
from conflict_interface.data_types.state import state_update
from conflict_interface.logger_config import get_logger
from conflict_interface.replay.replay_patch import BidirectionalReplayPatch
from conflict_interface.replay.replay_patch import PathNode
from conflict_interface.replay.replay_patch import ReplayPatch

logger = get_logger()


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

    def update(self, other: "ResourceState", path: list[PathNode] = None, rp: BidirectionalReplayPatch = None):
        state_update(self, other, path=path, rp=rp)
        if rp:
            if self.resource_profiles != other.resource_profiles:
                rp.replace(path + ["resource_profiles"], self.resource_profiles, other.resource_profiles)
            if self.trading != other.trading:
                rp.replace(path + ["trading"], self.trading, other.trading)
            if self.bids != other.bids:
                rp.replace(path + ["bids"], self.bids, other.bids)
            if self.asks != other.asks:
                rp.replace(path + ["asks"], self.asks, other.asks)
            if self.prices != other.prices:
                rp.replace(path + ["prices"], self.prices, other.prices)
        self.resource_profiles = other.resource_profiles
        self.trading = other.trading
        self.bids = other.bids
        self.asks = other.asks
        self.prices = other.prices

    def get_order(self, buy: bool , resource_type: ResourceType = -1, piece_price: float = -1, amount: int = -1, order_id: int = -1) -> Optional[Order]:
        for inner in self.bids if buy else self.asks:
            for order in inner:
                if order.order_id == order_id or (order.resource_type == resource_type and order.limit == piece_price and order.amount == amount):
                    return order

        logger.warning(f"Order not found for resource_type: {resource_type}, piece_price: {piece_price}, amount: {amount}, buy: {buy}")
        return None

    def cancel_order(self, order: Order) -> tuple[Optional[int], OrderActionResult]:
        if order is None:
            return None, OrderActionResult.ORDER_NOT_FOUND

        action = OrderAction(order = order, cancel=True)
        return self.game.online.do_action(action), OrderActionResult.OK

    def check_sell_trade_allowed(self, resource_type: ResourceType, piece_price: float, amount: int) -> OrderActionResult:
        resource_entry = self.game.get_resource_entry(resource_type)
        if resource_entry is None:
            return OrderActionResult.RESOURCE_ENTRY_MISSING

        if piece_price > resource_entry.max_price:
            return OrderActionResult.PRICE_TO_HIGH
        elif piece_price < resource_entry.min_price:
            return OrderActionResult.PRICE_TO_LOW

        if amount < 1:
            return OrderActionResult.AMOUNT_TO_LOW
        if amount > resource_entry.get_resource_amount():
            return OrderActionResult.AMOUNT_TO_HIGH

        return OrderActionResult.OK

    def create_ask(self, resource_type: ResourceType, piece_price: float, amount: int) -> tuple[Optional[int], OrderActionResult]: # Offer to Sell resource to anyone
        result = self.check_sell_trade_allowed(resource_type, piece_price, amount)
        if result != OrderActionResult.OK:
            return None, result

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
        return self.game.online.do_action(action), result

    def check_buy_trade_allowed(self, resource_type: ResourceType, piece_price: float, amount: int) -> OrderActionResult:
        resource_entry = self.game.get_resource_entry(resource_type)
        money_entry = self.game.get_resource_entry(ResourceType.MONEY)
        if resource_entry is None:
            return OrderActionResult.RESOURCE_ENTRY_MISSING

        if amount*piece_price > money_entry.get_resource_amount():
            return OrderActionResult.NOT_ENOUGH_MONEY

        return OrderActionResult.OK

    def create_bid(self, resource_type: ResourceType, piece_price: float, amount: int) -> tuple[Optional[int], OrderActionResult]: # Ask to Buy resource from anyone
        result = self.check_buy_trade_allowed(resource_type, piece_price, amount)
        if result != OrderActionResult.OK:
            return None, result

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
        return self.game.online.do_action(action), result