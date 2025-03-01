from __future__ import annotations

from datetime import datetime

from dataclasses import dataclass

from conflict_interface.data_types.resource_state.resource_profile import ResourceProfile
from conflict_interface.data_types.custom_types import HashMap, BidListOuter, BidListInner, AskListOuter, AskListInner
from conflict_interface.data_types.game_object import GameObject
from conflict_interface.data_types.resource_state.order import Order
from conflict_interface.data_types.resource_state.trading import Trading


@dataclass
class ResourceState(GameObject):
    C = "ultshared.UltResourceState"
    STATE_ID = 4
    resource_profiles: HashMap[int, ResourceProfile]

    state_type: int  # should be the same as STATE_ID
    time_stamp: datetime
    state_id: str  # Is not the STATE_ID above

    trading: Trading
    bids: BidListOuter[BidListInner[Order]]
    asks: AskListOuter[AskListInner[Order]]
    prices: list[float] # Has to be floats


    MAPPING = {
        "resource_profiles": "resourceProfs",
        "state_type": "stateType",
        "time_stamp": "timeStamp",
        "state_id": "stateID",
        "trading": "trading",
        "bids": "bids",
        "asks": "asks",
        "prices": "prices",
    }