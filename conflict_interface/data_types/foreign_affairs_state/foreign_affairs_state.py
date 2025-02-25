from __future__ import annotations
from typing import TYPE_CHECKING
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


@dataclass
class ForeignAffairRelations(GameObject):
    C = "ultshared.ForeignAffairRelations"
    # TODO Implement
    # neighbor_relations: dict[int, dict[int, ForeignAffairRelationTypes]]
    pass
    """
    MAPPING = {
        "neighbor_relations": ConMapping("neighborRelations", dict[str, dict[str, int]])
    }
    """


@dataclass
class ForeignAffairsState(GameObject):
    C = "ultshared.ForeignAffairsState"
    STATE_ID = 5
    relations: ForeignAffairRelations
    MAPPING = {
        "relations": "relations"
    }