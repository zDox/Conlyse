from dataclasses import dataclass
from datetime import datetime


from data_types.utils import JsonMappedClass, MappedValue, \
        unixtimestamp_to_datetime


@dataclass
class Article(JsonMappedClass):
    sender_id: int
    receiver_id: int
    message_id: int
    time_stamp: datetime

    title: str
    author: str  # Theme of article
    message_body: str

    mapping = {
        "sender_id": "senderID",
        "receiver_id": "receiverID",
        "message_id": "messageUID",
        "time_stamp": MappedValue("timeStamp",
                                  unixtimestamp_to_datetime),

        "title": "title",
        "author": "author",
        "message_body": "messageBody",
    }
