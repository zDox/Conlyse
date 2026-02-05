from dataclasses import dataclass

from conflict_interface.data_types.custom_types import DateTimeMillisecondsInt
from conflict_interface.data_types.custom_types import SqlDate
from conflict_interface.game_object.game_object import GameObject
from conflict_interface.game_object.game_object_binary import SerializationCategory
from conflict_interface.game_object.decorators import binary_serializable
from conflict_interface.replay.replay_patch import BidirectionalReplayPatch
from conflict_interface.replay.constants import PathNode


@binary_serializable(SerializationCategory.DATACLASS)
@dataclass
class StatisticsArticle(GameObject):
    C = "ultshared.UltStatisticsArticle"
    message_body: str
    date: SqlDate[DateTimeMillisecondsInt] # sql date format
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

    def update(self, other: "StatisticsArticle", path: list[PathNode] = None, rp: BidirectionalReplayPatch = None):
        for attr in self.get_mapping():
            if getattr(self, attr) != getattr(other, attr):
                if rp:
                    rp.replace(path + [attr],
                               getattr(self, attr),
                               getattr(other, attr))
                setattr(self, attr, getattr(other, attr))