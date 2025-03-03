from dataclasses import dataclass

from conflict_interface.data_types.game_object import GameObject


@dataclass
class Sender(GameObject):
    C = "ultshared.gameevents.UltSender"

    sender_id: int
    nation_name: str

    MAPPING = {
        "sender_id": "senderID",
        "nation_name": "nationName",

    }

