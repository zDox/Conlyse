from enum import EnumMeta
from datetime import datetime, timedelta
from typing import TypeVar

from conflict_interface.data_types.game_object_binary import SerializationCategory
from conflict_interface.data_types.game_object_binary import binary_serializable

K = TypeVar("K")
V = TypeVar("V")

@binary_serializable(SerializationCategory.LIST)
class UnitList(list):
    C = "[Lultshared.warfare.UltUnit;"

@binary_serializable(SerializationCategory.LIST)
class ProductionList(list):
    C = "ultshared.UltProductionList"

@binary_serializable(SerializationCategory.LIST)
class BidListOuter(list):
    C = "[Lultshared.UltBidList;" # TODO maby a better way to do this but its the most generic also
                                  # They are just stupid for using 2 different types of lists
@binary_serializable(SerializationCategory.LIST)
class  BidListInner(list):
    C = "ultshared.UltBidList"

@binary_serializable(SerializationCategory.LIST)
class AskListOuter(list):
    C = "[Lultshared.UltAskList;"

@binary_serializable(SerializationCategory.LIST)
class AskListInner(list):
    C = "ultshared.UltAskList"

@binary_serializable(SerializationCategory.LIST)
class RankingEntryList(list):
    C = "[Lultshared.UltRankingEntry;"

@binary_serializable(SerializationCategory.LIST)
class LinkedList(list):
    C = "java.util.LinkedList"

@binary_serializable(SerializationCategory.LIST)
class Vector(list):
    C = "java.util.Vector"

@binary_serializable(SerializationCategory.LIST)
class ArrayList(list):
    C = "java.util.ArrayList"

@binary_serializable(SerializationCategory.LIST)
class ArraysArrayList(list):
    C = "java.util.Arrays$ArrayList"

@binary_serializable(SerializationCategory.LIST)
class EmptyList(list):
    C = "java.util.Collections$EmptyList"

@binary_serializable(SerializationCategory.LIST)
class UnmodifiableCollection(list):
    C = "java.util.Collections$UnmodifiableCollection"

@binary_serializable(SerializationCategory.LIST)
class SqlDate(list):
    """
    A list that represents a SQL date. It is used to convert the date to a string
    """
    C = "java.sql.Date"

@binary_serializable(SerializationCategory.LIST)
class HashSet(list):
    C = "java.util.HashSet"

@binary_serializable(SerializationCategory.DICT)
class HashSetMap(dict):
    """
    Dictionary in python but HashSet in Conflict. Used for performance of lookups.
    """
    C = "java.util.HashSet"

@binary_serializable(SerializationCategory.LIST)
class UnmodifiableSet(list):
    C = "java.util.Collections$UnmodifiableSet"

@binary_serializable(SerializationCategory.DICT)
class HashMap(dict[K, V]):
    C = "java.util.HashMap"

@binary_serializable(SerializationCategory.DICT)
class LinkedHashMap(dict):
    C = "java.util.LinkedHashMap"

@binary_serializable(SerializationCategory.DICT)
class TreeMap(dict):
    C = "java.util.TreeMap"

@binary_serializable(SerializationCategory.DICT)
class RegularImmutableMap(dict):
    C = "com.google.common.collect.RegularImmutableMap"

@binary_serializable(SerializationCategory.DICT)
class EmptyMap(dict):
    C = "java.util.Collections$EmptyMap"

@binary_serializable(SerializationCategory.DICT)
class UnmodifiableMap(dict):
    C = "java.util.Collections$UnmodifiableMap"

@binary_serializable(SerializationCategory.DATETIME)
class DateTimeMillisecondsStr(datetime):
    pass

@binary_serializable(SerializationCategory.DATETIME)
class DateTimeMillisecondsInt(datetime):
    pass

@binary_serializable(SerializationCategory.TIMEDELTA)
class TimeDeltaMillisecondsStr(timedelta):
    pass

@binary_serializable(SerializationCategory.TIMEDELTA)
class TimeDeltaMillisecondsInt(timedelta):
    pass

@binary_serializable(SerializationCategory.DATETIME)
class DateTimeSecondsStr(datetime):
    pass

@binary_serializable(SerializationCategory.DATETIME)
class DateTimeSecondsInt(datetime):
    pass

@binary_serializable(SerializationCategory.TIMEDELTA)
class TimeDeltaSecondsStr(timedelta):
    pass

@binary_serializable(SerializationCategory.TIMEDELTA)
class TimeDeltaSecondsInt(timedelta):
    pass

@binary_serializable(SerializationCategory.ENUM)
class DefaultEnumMeta(EnumMeta):
    """
    A Metaclass which makes the first entry of an Enum its
    default value
    """
    default = object()

    def __call__(cls, value=default, *args, **kwargs):
        if value is DefaultEnumMeta.default:
            # Assume the first enum is default
            return next(iter(cls))
        return super().__call__(value, *args, **kwargs)

    def get_value_type(cls):
        if len(cls) == 0:
            return None
        else:
            return type(next(iter(cls)).value)