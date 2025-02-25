from conflict_interface.data_types.game_object import GameObject
from dataclasses import dataclass
from datetime import datetime



@dataclass
class Article(GameObject):
    C = "ultshared.UltArticle"
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
