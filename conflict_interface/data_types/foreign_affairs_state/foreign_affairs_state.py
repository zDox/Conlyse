from dataclasses import dataclass
from dataclasses import field
from typing import Optional

from conflict_interface.data_types.custom_types import DateTimeMillisecondsInt
from conflict_interface.data_types.custom_types import HashMap
from conflict_interface.data_types.custom_types import Vector
from conflict_interface.data_types.foreign_affairs_state.foreign_affairs_state_enums import ForeignAffairRelationTypes
from conflict_interface.data_types.game_object import GameObject
from conflict_interface.data_types.game_object_binary import SerializationCategory
from conflict_interface.data_types.decorators import binary_serializable
from conflict_interface.data_types.newspaper_state.article import Article
from conflict_interface.data_types.state import State
from conflict_interface.data_types.state import state_update
from conflict_interface.data_types.state import universal_update
from conflict_interface.replay.replay_patch import BidirectionalReplayPatch
from conflict_interface.replay.replay_patch import PathNode

def dict_update(original: dict, other: dict, path: list[PathNode] = None, rp: BidirectionalReplayPatch = None):
    for key, value in other.items():
        if key not in original:
            if rp:
                rp.add(path + [key], None, value)
            original[key] = value
        else:
            if original[key] != value:
                if rp:
                    rp.replace(path + [key], original[key], value)
                original[key] = value
    for key in list(original.keys()):
        if key not in other:
            if rp:
                rp.remove(path + [key], original[key])
            del original[key]

@binary_serializable(SerializationCategory.DATACLASS)
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

    def update(self, other: "ForeignAffairRelations", path: list[PathNode] = None, rp: BidirectionalReplayPatch = None):
        if self.state_id != other.state_id:
            if rp:
                rp.replace(path + ["state_id"], self.state_id, other.state_id)
            self.state_id = other.state_id
        if self.players != other.players:
            if rp:
                rp.replace(path + ["players"], self.players, other.players)
            self.players = other.players
        dict_update(self.end_of_honor_period, other.end_of_honor_period, path + ["end_of_honor_period"], rp)
        dict_update(self.neighbor_relations, other.neighbor_relations, path + ["neighbor_relations"], rp)


    def get_relation(self, sender_id: int, receiver_id: int) -> Optional[ForeignAffairRelationTypes]:
        relations = self.neighbor_relations.get(sender_id-1)
        if relations is None:
            return None
        return relations.get(receiver_id-1, ForeignAffairRelationTypes.PEACE)

@binary_serializable(SerializationCategory.DATACLASS)
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

    def update(self, other: "ForeignAffairsState", path: list[PathNode] = None, rp: BidirectionalReplayPatch = None):
        state_update(self, other, path, rp)
        self.relations.update(other.relations, path + ["relations"], rp)
        if rp:
            rp.replace([*path, "messages"], self.messages, other.messages)
        self.messages = other.messages