from __future__ import annotations

from datetime import datetime
from typing import Optional

from ..custom_types import HashMap, Vector # TODO Find out why only relative import is working
from conflict_interface.data_types.game_object import GameObject

from dataclasses import dataclass

from enum import Enum

from ..state import State


class ForeignAffairRelationTypes(Enum):
    """
    Enumeration representing in which Relation two countries are.

    Attributes:
        WAR (int): The sender is in war with the receiver.
        CEASEFIRE (int): The sender is in ceasefire with the receiver.
        TRADE_EMBARGO (int): The sender established a trade embargo with the receiver.
        PEACE (int): The sender is in peace with the receiver.
        NON_AGGRESSION_PACT (int): The sender has a non-aggression pact with the receiver.
        RIGHT_OF_WAY (int): The sender has the right to send units through the receiver's country.
        VIEW_MILITARY_ACTIONS (int): The sender can view military actions of the receiver.
        MUTUAL_PROTECTION (int): The sender has made a mutual protection agreement with the receiver.
        SHARED_INTELLIGENCE (int): The sender shares intelligence with the receiver.
        MILITARY_AUTHORITY (int): The sender has military authority over the receiver.
        MAX (int): Represents the maximum applicable state for foreign relations.
    """
    WAR = -2
    CEASEFIRE = -1
    TRADE_EMBARGO = 0
    PEACE = 1
    NON_AGGRESSION_PACT = 2
    RIGHT_OF_WAY = 3
    VIEW_MILITARY_ACTIONS = 4
    MUTUAL_PROTECTION = 5
    SHARED_INTELLIGENCE = 6
    MILITARY_AUTHORITY = 7
    MAX = 99


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

        neighbor_relations (dict[int, dict[int, ForeignAffairRelationTypes]]):
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

    state_id: int # TODO why is here a state_id?
    players: int
    end_of_honor_period: HashMap[int, datetime] # TODO no idea if this is correct (no examples in data1)


    neighbor_relations: dict[int, dict[int, ForeignAffairRelationTypes]]
    MAPPING = {
        "neighbor_relations": "neighborRelations",
        "state_id": "stateID",
        "players": "players",
        "end_of_honor_period": "endOfHonorPeriod",
    }


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
    messages: Vector[str]  # TODO no idea if its a string vector (no examples in data1)
    MAPPING = {
        "relations": "relations",
        "messages": "messages",
    }