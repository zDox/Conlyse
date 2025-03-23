from dataclasses import dataclass
from dataclasses import field
from typing import Optional

from conflict_interface.data_types.custom_types import DateTimeMillisecondsInt
from conflict_interface.data_types.custom_types import HashMap
from conflict_interface.data_types.custom_types import Vector
from conflict_interface.data_types.foreign_affairs_state.foreign_affairs_state_enums import ForeignAffairRelationTypes
from conflict_interface.data_types.game_object import GameObject
from conflict_interface.data_types.newspaper_state.article import Article
from conflict_interface.data_types.state import State
from conflict_interface.replay.replay_patch import BidirectionalReplayPatch
from conflict_interface.replay.replay_patch import PathNode
from conflict_interface.replay.replay_patch import ReplayPatch


@dataclass
class ForeignAffairRelations(GameObject):
    """
    Represents foreign affair relations in the context of the game.
    Fog of war does not apply to this data. One can see the relations
    of other players with other players.

    Attributes:
        state_id (int): Identifier for the state related to these foreign
        affairs.

        players (int): Represents the number of players.

        end_of_honor_period (HashMap[int, datetime]): Maps an identifier
        to a datetime indicating when an "honor period" ends for a player.

        neighbor_relations (dict[int, dict[int, conflict_interface.data_types.foreign_affairs_state.foreign_affairs_state_enums.ForeignAffairRelationTypes]]):
        Represents the diplomatic relationships the key of the top level dict is
        the sender and the value is a dict with the receiver as the key and the
        value of that dict is the ForeignAffairRelationType. One has to
        subtract 1 of both of these identifiers to get the actual player id.
        For example, if Italy(originally 15) is at war with Spain(originally 97),
        then there would be the entry {14: {96: ForeignAffairRelationTypes.WAR}}.
        The relation is not symmetric. Hence, Italy could be at war with Spain but
        Spain not at war with Italy.

    """
    C = "ultshared.UltForeignAffairRelations"

    state_id: int
    players: int = None
    end_of_honor_period: HashMap[int, DateTimeMillisecondsInt] = field(default_factory=dict)# TODO no idea if this is correct (no examples in data1)


    neighbor_relations: dict[int, dict[int, ForeignAffairRelationTypes]] = field(default_factory=dict)
    MAPPING = {
        "state_id": "stateID",
        "neighbor_relations": "neighborRelations",
        "players": "players",
        "end_of_honor_period": "endOfHonorPeriod",
    }

    def get_relation(self, sender_id: int, receiver_id: int) -> Optional[ForeignAffairRelationTypes]:
        relations = self.neighbor_relations.get(sender_id-1)
        if relations is None:
            return None
        return relations.get(receiver_id-1, ForeignAffairRelationTypes.PEACE)


@dataclass
class ForeignAffairsState(State):
    """
    This class models the foreign affairs state, including relationships and communication messages.

    Attributes:
        C: A constant class identifier for the ultimate foreign affairs state.
        STATE_TYPE: An integer representing the type of state, set to 5 for this particular state type.
        relations (ForeignAffairRelations): Represents the foreign affair relationships in the state.
        messages (Vector[str]): A collection of message strings that are likely a vector of string types, though
        the exact implementation details remain uncertain.
        MAPPING (dict): A dictionary mapping class attributes to their corresponding representation keys.
    """
    C = "ultshared.UltForeignAffairsState"
    STATE_TYPE = 5
    relations: ForeignAffairRelations
    messages: Vector[Article] = field(default_factory=list)
    MAPPING = {
        "relations": "relations",
        "messages": "messages",
    }