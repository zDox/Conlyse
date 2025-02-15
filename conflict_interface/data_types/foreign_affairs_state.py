from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from conflict_interface.game_interface import GameInterface
from conflict_interface.utils import GameObject

from dataclasses import dataclass


@dataclass
class ForeignAffairsState(GameObject):
    STATE_ID = 5
    relationships: dict[int, dict[int, int]]

    @classmethod
    def from_dict(cls, obj, game: GameInterface = None):
        relationships = {int(sender_id)+1: {int(receiver_id)+1:
                                            int(relation)}
                         for sender_id, sender
                         in obj["relations"]["neighborRelations"].items()
                         for receiver_id, relation in sender.items()}

        instance = cls(**{
            "relationships": relationships,
            })
        instance.game = game
        return instance