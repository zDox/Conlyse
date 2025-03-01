from dataclasses import dataclass

from conflict_interface.data_types.game_object import GameObject

@dataclass
class StatisticsArticle(GameObject):
    C = "ultshared.UltStatisticsArticle"
    message_body: str
    date: list[str] # sql date format
    time: list[str] # sql time format
    author: str
    read_by_sender: bool
    read_by_receiver: bool
    deleted_by_sender: bool
    deleted_by_receiver: bool
    message_id: int
    author_id: int
    title: str
    day: int
    extended: int
    sender_flag_id: int
    receiver_flag_id: int
    report_count: int
    alliance_id: int
    shown_ranks: int
    time_stamp: int

    sender_id: int = -1
    receiver_id: int = -1


    MAPPING = {
        "message_body": "messageBody",
        "date": "date",
        "time": "time",
        "author": "author",
        "read_by_sender": "readBySender",
        "read_by_receiver": "readByReceiver",
        "deleted_by_sender": "deletedBySender",
        "deleted_by_receiver": "deletedByReceiver",
        "message_id": "messageUID",
        "author_id": "authorID",
        "title": "title",
        "day": "day",
        "extended": "extended",
        "sender_flag_id": "senderFlagID",
        "receiver_flag_id": "receiverFlagID",
        "report_count": "reportCount",
        "alliance_id": "allianceID",
        "shown_ranks": "shownRanks",
        "time_stamp": "timeStamp",
        "sender_id": "senderID",
        "receiver_id": "receiverID"
    }