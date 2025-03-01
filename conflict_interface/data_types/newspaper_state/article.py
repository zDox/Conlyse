from typing import Optional

from conflict_interface.data_types.custom_types import Vector
from conflict_interface.data_types.game_object import GameObject
from dataclasses import dataclass

from conflict_interface.data_types.newspaper_state.report_article import ReportArticle


@dataclass
class Article(GameObject):
    C = "ultshared.UltArticle"


    time_stamp: int

    title: str
    author: str  # Theme of article
    message_body: str

    address: Optional[str]
    receiver: Optional[str]
    read_by_sender: bool
    read_by_receiver: bool
    deleted_by_sender: bool
    deleted_by_receiver: bool
    author_id: int
    day: int
    extended: int
    intercepted: Optional[Vector[int]] # TODO: Check if int is the correct type
    sender_flag_id: int
    receiver_flag_id: int
    report_count: int
    alliance_id: int
    date: list[str] # sql date format
    time: list[str] # sql time format


    image_id: Optional[dict[str, int]]



    sender_id: int = -1
    receiver_id: int = -1
    message_id: int = -1



    MAPPING = {
        "time_stamp": "timeStamp",
        "title": "title",
        "author": "author",
        "message_body": "messageBody",
        "address": "address",
        "receiver": "receiver",
        "read_by_sender": "readBySender",
        "read_by_receiver": "readByReceiver",
        "deleted_by_sender": "deletedBySender",
        "deleted_by_receiver": "deletedByReceiver",
        "author_id": "authorID",
        "day": "day",
        "extended": "extended",
        "intercepted": "intercepted",
        "sender_flag_id": "senderFlagID",
        "receiver_flag_id": "receiverFlagID",
        "report_count": "reportCount",
        "alliance_id": "allianceID",
        "sender_id": "senderID",
        "receiver_id": "receiverID",
        "message_id": "messageUID",
        "date": "date",
        "time": "time",
        "image_id": "imageID",
    }
