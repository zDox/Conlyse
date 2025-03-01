from dataclasses import dataclass

from conflict_interface.data_types.game_object import GameObject
from conflict_interface.data_types.custom_types import HashMap


@dataclass
class TradeOffer(GameObject):
    C = "ultshared.UltTradeOffer"
    trade_id: int
    party_A: int
    party_B: int
    offers_A: HashMap[int, int] # TODO maby Profile ID, amount?
    offers_B: HashMap[int, int]
    processed: bool
    successful: bool
    time_stamp: int
    deleted_by_sender: bool
    read_by_receiver: bool
    deleted_by_receiver: bool
    message: str

    MAPPING = {
        "trade_id": "tradeId", # Why the fuck is it a lowercase d here. (already double-checked)
        "party_A": "partyA",
        "party_B": "partyB",
        "offers_A": "offersA",
        "offers_B": "offersB",
        "time_stamp": "timeStamp",
        "deleted_by_sender": "delBySender",
        "read_by_receiver": "readByReceiver",
        "deleted_by_receiver": "delByReceiver",
        "processed": "processed",
        "successful": "successful",
        "message": "message",
    }
