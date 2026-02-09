from dataclasses import dataclass
from typing import Optional

from conflict_interface.game_object.game_object import GameObject
from ..custom_types import HashMap
from ..custom_types import Vector
from conflict_interface.game_object.game_object_binary import SerializationCategory
from conflict_interface.game_object.decorators import conflict_serializable
from ..resource_state.trade_offer import TradeOffer
from ..resource_state.trading_profile import TradingProfile

from ..version import VERSION
@conflict_serializable(SerializationCategory.DATACLASS, version = VERSION)
@dataclass
class Trading(GameObject):
    C = "ultshared.UltTrading"

    state_id: int
    trading_offers: Vector[TradeOffer]
    past_trades: Optional[Vector[TradeOffer]]
    trading_profiles: Optional[HashMap[int, TradingProfile]]
    next_trade_id: int

    MAPPING = {
        "state_id": "stateID",
        "trading_offers": "tradingOffers",
        "past_trades": "pastTrades",
        "trading_profiles": "tradingProfiles",
        "next_trade_id": "nextTradeID",
    }