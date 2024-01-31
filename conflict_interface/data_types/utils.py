from typing import get_type_hints
from dataclasses import dataclass
from datetime import datetime, timedelta
from math import sqrt
from enum import EnumMeta

# Helper functions for parsing a mapped value


def timestamp_to_datetime(timestamp):
    return datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S") \
            if timestamp else None


def unixtimestamp_to_datetime(timestamp):
    if timestamp is None:
        return None

    if len(str(timestamp)) == 10:
        return datetime.utcfromtimestamp(int(timestamp))
    elif len(str(timestamp)) == 13:
        return datetime.utcfromtimestamp(int(timestamp)/1000)


def seconds_to_timedelta(seconds):
    if seconds is None:
        return None
    else:
        return timedelta(seconds=seconds)


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


@dataclass
class Position:
    x: float
    y: float

    @classmethod
    def from_dict(cls, obj):
        return cls(x=obj["x"], y=obj["y"])

    def distance(self, other):
        return sqrt((other.x - self.y) ** 2 + (other.y - self.y) ** 2)


@dataclass
class MappedValue:
    """
    Attributes
    ----------
    original : str
        the sound that the animal makes
    function : callable
        a function which needs to be called to convert
        between the conflict of nations value and python representation
    needs_entire_obj : bool
        the function needs the entire json object
    """

    original: str
    function: callable = None
    needs_entire_obj: bool = False


class JsonMappedClass:
    """
    JsonMappedClass is a class which should be inhereted by
    a dataclass, which should have a mapping between
    the field from the conflict of nations server and the
    python representation. A mapping is a dict where the keys
    are the field name and the value is a MappedValue.
    """
    @classmethod
    def from_dict(cls, obj: dict):
        parsed_data = {}
        resolved = get_type_hints(cls)

        for new_name, mapped_value in cls.mapping.items():
            ftype = resolved[new_name]
            if not isinstance(mapped_value, MappedValue):
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
