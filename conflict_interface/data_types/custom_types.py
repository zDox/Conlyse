from enum import EnumMeta


class LinkedList(list):
    C = "java.util.LinkedList"


class Vector(list):
    C = "java.util.Vector"


class ArrayList(list):
    C = "java.util.ArrayList"


class UnmodifiableCollection(list):
    C = "java.util.Collections$UnmodifiableCollection"


class HashSet(set):
    C = "java.util.HashSet"


class HashMap(dict):
    C = "java.util.HashMap"


class LinkedHashMap(dict):
    C = "LinkedHashMap"


class TreeMap(dict):
    C = "TreeMap"


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