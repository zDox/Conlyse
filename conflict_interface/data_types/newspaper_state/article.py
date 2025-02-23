from conflict_interface.utils import GameObject

from dataclasses import dataclass
from datetime import datetime


from conflict_interface.utils import ConMapping, \
        unixtimestamp_to_datetime


@dataclass
class Article(GameObject):
    sender_id: int
    receiver_id: int
    message_id: int
    time_stamp: datetime

    title: str
    author: str  # Theme of article
    message_body: str

    MAPPING = {
        "sender_id": "senderID",
        "receiver_id": "receiverID",
        "message_id": "messageUID",
        "time_stamp": "timeStamp",
        "title": "title",
        "author": "author",
        "message_body": "messageBody",
    }
