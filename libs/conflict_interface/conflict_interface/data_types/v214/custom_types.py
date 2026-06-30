from datetime import datetime
from datetime import timedelta
from typing import TypeVar

from conflict_interface.game_object.decorators import conflict_serializable, parse_edge_case
from conflict_interface.game_object.game_object_binary import SerializationCategory
from .version import VERSION

K = TypeVar("K")
V = TypeVar("V")


@conflict_serializable(SerializationCategory.LIST, version=VERSION)
class UnitList(list[V]):
    C = "[Lultshared.warfare.UltUnit;"


@conflict_serializable(SerializationCategory.LIST, version=VERSION)
class ProductionList(list[V]):
    C = "ultshared.UltProductionList"


@conflict_serializable(SerializationCategory.LIST, version=VERSION)
class BidListOuter(list[V]):
    C = "[Lultshared.UltBidList;"  # TODO maby a better way to do this but its the most generic also they are just stupid for using 2 different types of lists


@conflict_serializable(SerializationCategory.LIST, version=VERSION)
class BidListInner(list[V]):
    C = "ultshared.UltBidList"


@conflict_serializable(SerializationCategory.LIST, version=VERSION)
class AskListOuter(list[V]):
    C = "[Lultshared.UltAskList;"


@conflict_serializable(SerializationCategory.LIST, version=VERSION)
class AskListInner(list[V]):
    C = "ultshared.UltAskList"


@conflict_serializable(SerializationCategory.LIST, version=VERSION)
class RankingEntryList(list[V]):
    C = "[Lultshared.UltRankingEntry;"


@conflict_serializable(SerializationCategory.LIST, version=VERSION)
class LinkedList(list[V]):
    C = "java.util.LinkedList"


@conflict_serializable(SerializationCategory.LIST, version=VERSION)
class Vector(list[V]):
    C = "java.util.Vector"


@conflict_serializable(SerializationCategory.LIST, version=VERSION)
class ArrayList(list[V]):
    C = "java.util.ArrayList"


@conflict_serializable(SerializationCategory.LIST, version=VERSION)
class ArraysArrayList(list[V]):
    C = "java.util.Arrays$ArrayList"


@conflict_serializable(SerializationCategory.LIST, version=VERSION)
class EmptyList(list[V]):
    C = "java.util.Collections$EmptyList"


@conflict_serializable(SerializationCategory.LIST, version=VERSION)
class UnmodifiableCollection(list[V]):
    C = "java.util.Collections$UnmodifiableCollection"

@parse_edge_case(tag="SqlDate", version=VERSION)
@conflict_serializable(SerializationCategory.LIST, version=VERSION)
class SqlDate(list[V]):
    """
    A list that represents a SQL date. It is used to convert the date to a string
    """
    C = "java.sql.Date"


@conflict_serializable(SerializationCategory.LIST, version=VERSION)
class HashSet(list[V]):
    C = "java.util.HashSet"


@conflict_serializable(SerializationCategory.DICT, version=VERSION)
class HashSetMap(dict[K, V]):
    """
    Dictionary in python but HashSet in Conflict. Used for performance of lookups.
    """
    C = "java.util.HashSet"


@conflict_serializable(SerializationCategory.LIST, version=VERSION)
class UnmodifiableSet(list[V]):
    C = "java.util.Collections$UnmodifiableSet"


@conflict_serializable(SerializationCategory.DICT, version=VERSION)
class HashMap(dict[K, V]):
    C = "java.util.HashMap"


@conflict_serializable(SerializationCategory.DICT, version=VERSION)
class LinkedHashMap(dict[K, V]):
    C = "java.util.LinkedHashMap"


@conflict_serializable(SerializationCategory.DICT, version=VERSION)
class TreeMap(dict):
    C = "java.util.TreeMap"


@conflict_serializable(SerializationCategory.DICT, version=VERSION)
class RegularImmutableMap(dict):
    C = "com.google.common.collect.RegularImmutableMap"


@conflict_serializable(SerializationCategory.DICT, version=VERSION)
class EmptyMap(dict):
    C = "java.util.Collections$EmptyMap"


@conflict_serializable(SerializationCategory.DICT, version=VERSION)
class UnmodifiableMap(dict):
    C = "java.util.Collections$UnmodifiableMap"


@conflict_serializable(SerializationCategory.DATETIME, version=VERSION)
class DateTimeMillisecondsStr(datetime):
    pass


@conflict_serializable(SerializationCategory.DATETIME, version=VERSION)
class DateTimeMillisecondsInt(datetime):
    pass


@conflict_serializable(SerializationCategory.TIMEDELTA, version=VERSION)
class TimeDeltaMillisecondsStr(timedelta):
    pass


@conflict_serializable(SerializationCategory.TIMEDELTA, version=VERSION)
class TimeDeltaMillisecondsInt(timedelta):
    pass


@conflict_serializable(SerializationCategory.DATETIME, version=VERSION)
class DateTimeSecondsStr(datetime):
    pass


@conflict_serializable(SerializationCategory.DATETIME, version=VERSION)
class DateTimeSecondsInt(datetime):
    pass


@conflict_serializable(SerializationCategory.TIMEDELTA, version=VERSION)
class TimeDeltaSecondsStr(timedelta):
    pass


@conflict_serializable(SerializationCategory.TIMEDELTA, version=VERSION)
class TimeDeltaSecondsInt(timedelta):
    pass


