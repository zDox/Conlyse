from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from conflict_interface.game_interface import GameInterface
from conflict_interface.utils import GameObject, HashMap, ConMapping

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
    neighbor_relations: dict[int, dict[int, ForeignAffairRelationTypes]]
    MAPPING = {
        "neighbor_relations": ConMapping("neighborRelations", dict[str, dict[str, int]])
    }


@dataclass
class ForeignAffairsState(GameObject):
    STATE_ID = 5
    relations: ForeignAffairRelations
    MAPPING = {
        "relations": "relations"
    }