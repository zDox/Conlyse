from dataclasses import dataclass
from typing import Optional

from conflict_interface.data_types.game_object import GameObject
from conflict_interface.data_types.custom_types import HashMap
from conflict_interface.data_types.custom_types import Vector
from conflict_interface.data_types.resource_state.trade_offer import TradeOffer
from conflict_interface.data_types.resource_state.trading_profile import TradingProfile


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