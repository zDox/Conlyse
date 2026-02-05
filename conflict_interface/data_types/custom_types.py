from datetime import datetime
from datetime import timedelta
from enum import EnumMeta
from typing import TypeVar

from conflict_interface.game_object.decorators import binary_serializable
from conflict_interface.game_object.game_object_binary import SerializationCategory
from conflict_interface.data_types.version import VERSION

K = TypeVar("K")
V = TypeVar("V")


@binary_serializable(SerializationCategory.LIST, version=VERSION)
class UnitList(list):
    C = "[Lultshared.warfare.UltUnit;"


@binary_serializable(SerializationCategory.LIST, version=VERSION)
class ProductionList(list):
    C = "ultshared.UltProductionList"


@binary_serializable(SerializationCategory.LIST, version=VERSION)
class BidListOuter(list):
    C = "[Lultshared.UltBidList;"  # TODO maby a better way to do this but its the most generic also
    # They are just stupid for using 2 different types of lists


@binary_serializable(SerializationCategory.LIST, version=VERSION)
class BidListInner(list):
    C = "ultshared.UltBidList"


@binary_serializable(SerializationCategory.LIST, version=VERSION)
class AskListOuter(list):
    C = "[Lultshared.UltAskList;"


@binary_serializable(SerializationCategory.LIST, version=VERSION)
class AskListInner(list):
    C = "ultshared.UltAskList"


@binary_serializable(SerializationCategory.LIST, version=VERSION)
class RankingEntryList(list):
    C = "[Lultshared.UltRankingEntry;"


@binary_serializable(SerializationCategory.LIST, version=VERSION)
class LinkedList(list):
    C = "java.util.LinkedList"


@binary_serializable(SerializationCategory.LIST, version=VERSION)
class Vector(list):
    C = "java.util.Vector"


@binary_serializable(SerializationCategory.LIST, version=VERSION)
class ArrayList(list):
    C = "java.util.ArrayList"


@binary_serializable(SerializationCategory.LIST, version=VERSION)
class ArraysArrayList(list):
    C = "java.util.Arrays$ArrayList"


@binary_serializable(SerializationCategory.LIST, version=VERSION)
class EmptyList(list):
    C = "java.util.Collections$EmptyList"


@binary_serializable(SerializationCategory.LIST, version=VERSION)
class UnmodifiableCollection(list):
    C = "java.util.Collections$UnmodifiableCollection"


@binary_serializable(SerializationCategory.LIST, version=VERSION)
class SqlDate(list):
    """
    A list that represents a SQL date. It is used to convert the date to a string
    """
    C = "java.sql.Date"


@binary_serializable(SerializationCategory.LIST, version=VERSION)
class HashSet(list):
    C = "java.util.HashSet"


@binary_serializable(SerializationCategory.DICT, version=VERSION)
class HashSetMap(dict):
    """
    Dictionary in python but HashSet in Conflict. Used for performance of lookups.
    """
    C = "java.util.HashSet"


@binary_serializable(SerializationCategory.LIST, version=VERSION)
class UnmodifiableSet(list):
    C = "java.util.Collections$UnmodifiableSet"


@binary_serializable(SerializationCategory.DICT, version=VERSION)
class HashMap(dict[K, V]):
    C = "java.util.HashMap"


@binary_serializable(SerializationCategory.DICT, version=VERSION)
class LinkedHashMap(dict):
    C = "java.util.LinkedHashMap"


@binary_serializable(SerializationCategory.DICT, version=VERSION)
class TreeMap(dict):
    C = "java.util.TreeMap"


@binary_serializable(SerializationCategory.DICT, version=VERSION)
class RegularImmutableMap(dict):
    C = "com.google.common.collect.RegularImmutableMap"


@binary_serializable(SerializationCategory.DICT, version=VERSION)
class EmptyMap(dict):
    C = "java.util.Collections$EmptyMap"


@binary_serializable(SerializationCategory.DICT, version=VERSION)
class UnmodifiableMap(dict):
    C = "java.util.Collections$UnmodifiableMap"


@binary_serializable(SerializationCategory.DATETIME, version=VERSION)
class DateTimeMillisecondsStr(datetime):
    pass


@binary_serializable(SerializationCategory.DATETIME, version=VERSION)
class DateTimeMillisecondsInt(datetime):
    pass


@binary_serializable(SerializationCategory.TIMEDELTA, version=VERSION)
class TimeDeltaMillisecondsStr(timedelta):
    pass


@binary_serializable(SerializationCategory.TIMEDELTA, version=VERSION)
class TimeDeltaMillisecondsInt(timedelta):
    pass


@binary_serializable(SerializationCategory.DATETIME, version=VERSION)
class DateTimeSecondsStr(datetime):
    pass


@binary_serializable(SerializationCategory.DATETIME, version=VERSION)
class DateTimeSecondsInt(datetime):
    pass


@binary_serializable(SerializationCategory.TIMEDELTA, version=VERSION)
class TimeDeltaSecondsStr(timedelta):
    pass


@binary_serializable(SerializationCategory.TIMEDELTA, version=VERSION)
class TimeDeltaSecondsInt(timedelta):
    pass


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
