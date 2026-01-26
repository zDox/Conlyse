from enum import Enum

from conflict_interface.data_types.game_object_binary import SerializationCategory
from conflict_interface.data_types.decorators import binary_serializable


@binary_serializable(SerializationCategory.ENUM)
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
