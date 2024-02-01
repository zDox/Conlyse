from dataclasses import dataclass


@dataclass
class ForeignAffairsState:
    STATE_ID = 5
    relationships: dict[int, dict[int, int]]

    @classmethod
    def from_dict(cls, obj):
        relationships = {int(sender_id)+1: {int(receiver_id)+1:
                                            int(relation)}
                         for sender_id, sender
                         in obj["relations"]["neighborRelations"].items()
                         for receiver_id, relation in sender.items()}

        return cls(**{
            "relationships": relationships,
            })
