from dataclasses import dataclass

from conflict_interface.game_object.game_object import GameObject
from ..custom_types import DateTimeMillisecondsInt
from ..custom_types import HashMap
from conflict_interface.game_object.game_object_binary import SerializationCategory
from conflict_interface.game_object.decorators import conflict_serializable


from ..version import VERSION
@conflict_serializable(SerializationCategory.DATACLASS, version = VERSION)
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
    expiry_date: DateTimeMillisecondsInt
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
        "expiry_date": "expiryDate",
        "deleted_by_sender": "delBySender",
        "read_by_receiver": "readByReceiver",
        "deleted_by_receiver": "delByReceiver",
        "processed": "processed",
        "successful": "successful",
        "message": "message",
    }


@conflict_serializable(SerializationCategory.DATACLASS, version = VERSION)
@dataclass
class AITradeOffer(GameObject):
    C = "ultshared.UltAITradeOffer"
    trade_id: int
    party_A: int
    party_B: int
    offers_A: HashMap[int, int]
    offers_B: HashMap[int, int]
    processed: bool
    successful: bool
    time_stamp: int
    expiry_date: DateTimeMillisecondsInt
    deleted_by_sender: bool
    read_by_receiver: bool
    deleted_by_receiver: bool
    message: str

    MAPPING = {
        "trade_id": "tradeId",
        "party_A": "partyA",
        "party_B": "partyB",
        "offers_A": "offersA",
        "offers_B": "offersB",
        "time_stamp": "timeStamp",
        "expiry_date": "expiryDate",
        "deleted_by_sender": "delBySender",
        "read_by_receiver": "readByReceiver",
        "deleted_by_receiver": "delByReceiver",
        "processed": "processed",
        "successful": "successful",
        "message": "message",
    }
