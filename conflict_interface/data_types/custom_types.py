from enum import EnumMeta


class UnitList(list):
    C = "[Lultshared.warfare.UltUnit;"

class ProductionList(list):
    C = "ultshared.UltProductionList"

class BidListOuter(list):
    C = "[Lultshared.UltBidList;" # TODO maby a better way to do this but its the most generic also
                                  # They are just stupid for using 2 different types of lists

class  BidListInner(list):
    C = "ultshared.UltBidList"

class AskListOuter(list):
    C = "[Lultshared.UltAskList;"

class AskListInner(list):
    C = "ultshared.UltAskList"

class LinkedList(list):
    C = "java.util.LinkedList"


class Vector(list):
    C = "java.util.Vector"


class ArrayList(list):
    C = "java.util.ArrayList"

class EmptyList(list):
    C = "java.util.Collections$EmptyList"

class UnmodifiableCollection(list):
    C = "java.util.Collections$UnmodifiableCollection"


class HashSet(set):
    C = "java.util.HashSet"


class HashMap(dict):
    C = "java.util.HashMap"


class LinkedHashMap(dict):
    C = "java.util.LinkedHashMap"


class TreeMap(dict):
    C = "java.util.TreeMap"

class RegularImmutableMap(dict):
    C = "com.google.common.collect.RegularImmutableMap"

class EmptyMap(dict):
    C = "java.util.Collections$EmptyMap"


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