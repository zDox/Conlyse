from typing import get_type_hints
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import EnumMeta, Enum
from .helper import unixtimestamp_to_datetime, seconds_to_timedelta


class UpdatableClass:
    def update(self, new_class):
        for field in self.__annotations__.keys():
            if not callable(getattr(field, "update", None)):
                continue

            self[field].update(new_class[field])


class DefaultEnumMeta(EnumMeta):
    """
    A Metaclass which makes the first entry of a Enum its
    default value
    """
    default = object()

    def __call__(cls, value=default, *args, **kwargs):
        if value is DefaultEnumMeta.default:
            # Assume the first enum is default
            return next(iter(cls))
        return super().__call__(value, *args, **kwargs)

class LinkedList(list):
    pass

class Vector(list):
    pass

class HashMap(dict):
    pass

class TreeMap(dict):
    pass


class JavaTypes(Enum):
    LinkedList = "java.util.LinkedList"
    HashMap = "java.util.HashMap"
    TreeMap = "java.util.TreeMap"
    Vector = "java.util.Vector"


@dataclass
class ConMapping:
    """
    Attributes
    ----------
    """

    con_key: str
    con_type: type


class JsonMappedClass:
    """
    JsonMappedClass is a class which should be inhereted by
    a dataclass, which should have a mapping between
    the field from the conflict of nations server and the
    python representation. A mapping is a dict where the keys
    are the field name and the value is a MappedValue.
    """
    MAPPING = {}

    @classmethod
    def from_dict(cls, obj: dict):
        parsed_data = {}
        resolved = get_type_hints(cls)

        for new_name, mapped_value in cls.MAPPING.items():
            ftype = resolved[new_name]
            if not isinstance(mapped_value, ConMapping):
                # bool should be default False
                if ftype is bool:
                    parsed_data[new_name] = ftype(obj.get(mapped_value))
                elif ftype is datetime:
                    parsed_data[new_name] = unixtimestamp_to_datetime(
                            obj.get(mapped_value))
                elif ftype is timedelta:
                    parsed_data[new_name] = seconds_to_timedelta(
                            obj.get(mapped_value))
                # if type has metaclass DefaultEnumMeta use its default init
                elif obj.get(mapped_value) is None \
                        and type(ftype) is DefaultEnumMeta:
                    parsed_data[new_name] = ftype()
                elif obj.get(mapped_value) is None:
                    parsed_data[new_name] = None

                # If Type has from_dict implemented, use it
                elif hasattr(ftype, "from_dict"):
                    parsed_data[new_name] = ftype.from_dict(
                            obj.get(mapped_value))
                else:
                    parsed_data[new_name] = ftype(obj.get(mapped_value))

            elif mapped_value.function:
                if mapped_value.needs_entire_obj:
                    parsed_data[new_name] = mapped_value.function(
                            obj, obj.get(mapped_value.original))
                else:
                    parsed_data[new_name] = mapped_value.function(
                            obj.get(mapped_value.original))
            else:
                parsed_data[new_name] = ftype(
                        obj.get(mapped_value.original))
        return cls(**parsed_data)
