from __future__ import annotations

from datetime import datetime
from typing import Optional

from ..custom_types import HashMap, Vector # TODO Find out why only relative import is working
from conflict_interface.data_types.game_object import GameObject

from dataclasses import dataclass

from enum import Enum


class ForeignAffairRelationTypes(Enum):
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
class ForeignAffairsState(GameObject):
    C = "ultshared.UltForeignAffairsState"
    STATE_ID = 5
    relations: ForeignAffairRelations
    state_type: int # should be the same as STATE_ID
    time_stamp: datetime
    state_id: str # Is not the STATE_ID above
    messages: Vector[str]  # TODO no idea if its a string vector (no examples in data1)
    MAPPING = {
        "relations": "relations",
        "state_type": "stateType",
        "time_stamp": "timeStamp",
        "state_id": "stateID",
        "messages": "messages",
    }