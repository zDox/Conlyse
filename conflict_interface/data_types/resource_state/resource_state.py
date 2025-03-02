from __future__ import annotations


from dataclasses import dataclass
from typing import Optional

from conflict_interface.data_types.resource_state.resource_profile import ResourceProfile
from conflict_interface.data_types.custom_types import HashMap, BidListOuter, BidListInner, AskListOuter, AskListInner
from conflict_interface.data_types.game_object import GameObject
from conflict_interface.data_types.resource_state.order import Order
from conflict_interface.data_types.resource_state.trading import Trading
from conflict_interface.data_types.state import State


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