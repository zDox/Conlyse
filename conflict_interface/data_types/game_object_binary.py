from dataclasses import fields
from dataclasses import is_dataclass
from datetime import UTC
from enum import Enum
from logging import getLogger
from typing import Any

import msgspec

logger = getLogger()

class SerializationCategory(Enum):
    DATACLASS = 1
    ENUM = 2
    LIST = 3
    DICT = 4
    DATETIME = 5
    TIMEDELTA = 6
    POINT = 7


def binary_serializable(category: SerializationCategory):
    def wrapper(cls):
        GameObjectSerializer.register(cls, category)
        return cls

    return wrapper

def get_mapping(cls):
    if hasattr(cls, 'get_mapping'):
        return cls.get_mapping()
    elif hasattr(cls, 'MAPPING'):
        return cls.MAPPING
    else:
        return [f.name for f in fields(cls)]


class GameObjectSerializer:
    _PRIMITIVES = frozenset({int, float, str, bool, type(None)})

    _CLASS_FROM_ID: dict[int, type] = {}
    _ID_FROM_CLASS: dict[type, int] = {}
    _CATEGORY: dict[type, SerializationCategory] = {}

    _FIELDS_CACHE: dict[type, tuple[str, ...]] = {}

    # Marker to distinguish [type_id, ... ] from plain lists
    _TYPE_MARKER = -1

    def __init__(self):
        self._encoder = msgspec.msgpack.Encoder()
        self._decoder = msgspec.msgpack.Decoder()

        
    @classmethod
    def register(cls, obj: type, category: SerializationCategory):
        """Register a type with its category."""
        type_id = len(cls._ID_FROM_CLASS)

        cls._CLASS_FROM_ID[type_id] = obj
        cls._ID_FROM_CLASS[obj] = type_id
        cls._CATEGORY[obj] = category

        if is_dataclass(obj):
            mapping = get_mapping(obj)
            if isinstance(mapping, dict):
                cls._FIELDS_CACHE[obj] = tuple(mapping.keys())
            else:
                cls._FIELDS_CACHE[obj] = tuple(mapping)



    def serialize(self, obj: Any) -> bytes:
        raw = self._to_raw(obj)
        obj =  self._encoder.encode(raw)
        return obj

    def _to_raw(self, obj: Any):
        if obj is None:
            return None

        t = type(obj)

        if t in self._PRIMITIVES:
            return obj

        if t is list:
            return [self._to_raw(v) for v in obj]

        if t is dict:
            return {"__dict__": [[self._to_raw(k), self._to_raw(v)] for k, v in obj.items()]}

        type_id = self._ID_FROM_CLASS[t]
        cat = self._CATEGORY[t]

        if cat == SerializationCategory.DATACLASS:
            field_names = self._FIELDS_CACHE[t]
            return [self._TYPE_MARKER, type_id, *[self._to_raw(getattr(obj, name)) for name in field_names]]

        elif cat == SerializationCategory.LIST:
            return [self._TYPE_MARKER, type_id, [self._to_raw(v) for v in obj]]

        elif cat == SerializationCategory.DICT:
            return [self._TYPE_MARKER, type_id, [[self._to_raw(k), self._to_raw(v)] for k, v in obj.items()]]

        elif cat == SerializationCategory.DATETIME:
            return [self._TYPE_MARKER, type_id, obj.timestamp()]

        elif cat == SerializationCategory.TIMEDELTA:
            return [self._TYPE_MARKER, type_id, obj.total_seconds()]

        elif cat == SerializationCategory.ENUM:
            return [self._TYPE_MARKER, type_id, obj.value]

        elif cat == SerializationCategory.POINT:
            return [self._TYPE_MARKER, type_id, obj.x, obj. y]

        raise RuntimeError(f"Unknown category type {cat}")

    def deserialize(self, data: bytes) -> object:
        """Deserialize bytes back to a game object."""
        raw = self._decoder.decode(data)
        obj =  self._from_raw(raw)
        return obj

    def _from_raw(self, data):
        if data is None:
            return None

        t = type(data)

        if t in self._PRIMITIVES:
            return data

        if t is dict:
            from_raw = self._from_raw
            return {from_raw(k): from_raw(v) for k, v in data["__dict__"]}


        if t is list:
            # Check if it's a registered type:  [MARKER, type_id, ...]
            if len(data) >= 2 and data[0] == self._TYPE_MARKER:
                return self._from_raw_registered(data)
            else:
                # Plain list
                from_raw = self._from_raw
                return [from_raw(v) for v in data]

        raise TypeError(f"Cannot deserialize:  {type(data)} \n {str(data)[:1000]}")

    def _from_raw_registered(self, data):
        """Handle deserialization of registered types."""
        type_id = data[1]
        cls = self._CLASS_FROM_ID[type_id]
        cat = self._CATEGORY[cls]
        from_raw = self._from_raw

        if cat == SerializationCategory.DATACLASS:
            field_names = self._FIELDS_CACHE[cls]
            kwargs = {name: from_raw(data[i + 2]) for i, name in enumerate(field_names)}
            instance = cls(**kwargs)
            instance.game = None
            return instance

        elif cat == SerializationCategory.LIST:
            return cls([from_raw(v) for v in data[2]])

        elif cat == SerializationCategory.DICT:
            return cls({from_raw(pair[0]): from_raw(pair[1]) for pair in data[2]})

        elif cat == SerializationCategory.DATETIME:
            return cls.fromtimestamp(data[2], UTC)

        elif cat == SerializationCategory.TIMEDELTA:
            return cls(seconds=data[2])

        elif cat == SerializationCategory.ENUM:
            return cls(data[2])

        elif cat == SerializationCategory.POINT:
            return cls(data[2], data[3])

        raise TypeError(f"Unknown category:  {cat}")

    def get_stats(self) -> dict:
        """Return statistics about registered types."""
        return {
            'total_types':  len(self._CLASS_FROM_ID),
            'dataclasses': sum(1 for c in self._CATEGORY.values() if c == SerializationCategory.DATACLASS),
            'enums': sum(1 for c in self._CATEGORY. values() if c == SerializationCategory.ENUM),
            'list_wrappers': sum(1 for c in self._CATEGORY.values() if c == SerializationCategory.LIST),
            'dict_wrappers': sum(1 for c in self._CATEGORY.values() if c == SerializationCategory.DICT)
        }