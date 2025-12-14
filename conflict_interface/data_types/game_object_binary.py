import importlib
import inspect
import pkgutil
from dataclasses import fields
from dataclasses import is_dataclass
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from enum import Enum
from logging import getLogger
from typing import Any

import msgspec

from conflict_interface. data_types.custom_types import HashSet
from conflict_interface.data_types. game_state. game_state import States
from conflict_interface.data_types. point import Point

logger = getLogger()


def get_mapping(cls):
    if hasattr(cls, 'get_mapping'):
        return cls.get_mapping()
    elif hasattr(cls, 'MAPPING'):
        return cls.MAPPING
    else:
        return [f.name for f in fields(cls)]


class GameObjectSerializer:
    _PRIMITIVES = frozenset({int, float, str, bool, type(None)})

    # Marker to distinguish [type_id, ... ] from plain lists
    _TYPE_MARKER = -1

    def __init__(self):
        self._encoder = msgspec.msgpack.Encoder()
        self._decoder = msgspec.msgpack.Decoder()

        self._class_from_id:  dict[int, type] = {}
        self._id_from_class:  dict[type, int] = {}
        self._category: dict[type, str] = {}

        self._fields_cache: dict[type, tuple[str, ...]] = {}

        self._preloaded = False

    def _register(self, cls: type, category: str):
        """Register a type with its category."""
        type_id = len(self._id_from_class)

        self._class_from_id[type_id] = cls
        self._id_from_class[cls] = type_id
        self._category[cls] = category

        if is_dataclass(cls):
            mapping = get_mapping(cls)
            if isinstance(mapping, dict):
                self._fields_cache[cls] = tuple(mapping.keys())
            else:
                self._fields_cache[cls] = tuple(mapping)

    def preload(self):
        if self._preloaded:
            return

        package = importlib.import_module('conflict_interface.data_types')

        for loader, module_name, is_pkg in pkgutil. walk_packages(
                package.__path__, package.__name__ + '.'
        ):
            try:
                module = importlib.import_module(module_name)

                for name, obj in inspect.getmembers(module, inspect.isclass):
                    if obj.__module__ != module_name:
                        continue

                    if obj in self._category:
                        continue

                    if obj is HashSet:
                        pass

                    if is_dataclass(obj):
                        self._register(obj, 'dataclass')
                    elif isinstance(obj, type) and issubclass(obj, Enum) and obj is not Enum:
                        self._register(obj, 'enum')
                    elif isinstance(obj, type) and issubclass(obj, list) and obj is not list:
                        self._register(obj, 'list')
                    elif isinstance(obj, type) and issubclass(obj, dict) and obj is not dict:
                        self._register(obj, 'dict')
                    elif isinstance(obj, type) and issubclass(obj, datetime):
                        self._register(obj, 'datetime')
                    elif isinstance(obj, type) and issubclass(obj, timedelta):
                        self._register(obj, 'timedelta')
                    elif obj is Point:
                        self._register(obj, 'point')

            except ImportError as e:
                logger.debug(f"Failed to load {module_name} because of ImportError: \n{e}")

        self._preloaded = True

    def serialize(self, obj: Any) -> bytes:
        if not self._preloaded:
            raise RuntimeError("Call preload() before serializing")
        return self._encoder.encode(self._to_raw(obj))

    def _to_raw(self, obj: Any):
        if obj is None:
            return None

        t = type(obj)

        if t in self._PRIMITIVES:
            return obj

        if t is list:
            to_raw = self._to_raw
            return [to_raw(v) for v in obj]

        if t is dict:
            to_raw = self._to_raw
            # FIX: Convert dict to list of [key, value] pairs to handle non-hashable keys
            return {"__dict__": [[to_raw(k), to_raw(v)] for k, v in obj.items()]}

        type_id = self._id_from_class[t]
        cat = self._category[t]

        marker = self._TYPE_MARKER
        to_raw = self._to_raw

        if cat == 'dataclass':
            field_names = self._fields_cache[t]
            return [marker, type_id, *[to_raw(getattr(obj, name)) for name in field_names]]

        elif cat == 'list':
            return [marker, type_id, [to_raw(v) for v in obj]]

        elif cat == 'dict':
            # FIX: Convert to list of [key, value] pairs for registered dict types too
            return [marker, type_id, [[to_raw(k), to_raw(v)] for k, v in obj.items()]]

        elif cat == 'datetime':
            return [marker, type_id, obj.timestamp()]

        elif cat == 'timedelta':
            return [marker, type_id, obj.total_seconds()]

        elif cat == 'enum':
            return [marker, type_id, obj.value]

        elif cat == 'point':
            return [marker, type_id, obj.x, obj. y]

        raise RuntimeError(f"Unknown category type {cat}")

    def deserialize(self, data: bytes) -> object:
        """Deserialize bytes back to a game object."""
        if not self._preloaded:
            raise RuntimeError("Call preload() before deserializing")
        return self._from_raw(self._decoder.decode(data))

    def _from_raw(self, data):
        if data is None:
            return None

        t = type(data)

        if t in self._PRIMITIVES:
            return data

        if t is dict:
            # FIX: Check if this is our special dict format
            if "__dict__" in data:
                from_raw = self._from_raw
                return {from_raw(k): from_raw(v) for k, v in data["__dict__"]}
            else:
                # Regular dict (shouldn't happen with new format, but keep for safety)
                from_raw = self._from_raw
                return {from_raw(k): from_raw(v) for k, v in data. items()}

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
        cls = self._class_from_id[type_id]
        cat = self._category[cls]
        from_raw = self._from_raw

        if cat == 'dataclass':
            field_names = self._fields_cache[cls]
            kwargs = {name: from_raw(data[i + 2]) for i, name in enumerate(field_names)}
            return cls(**kwargs)

        elif cat == 'list':
            return cls([from_raw(v) for v in data[2]])

        elif cat == 'dict':
            # FIX:  Reconstruct from list of [key, value] pairs
            return cls({from_raw(pair[0]): from_raw(pair[1]) for pair in data[2]})

        elif cat == 'datetime':
            return cls. fromtimestamp(data[2], UTC)

        elif cat == 'timedelta':
            return cls(seconds=data[2])

        elif cat == 'enum':
            return cls(data[2])

        elif cat == 'point':
            return cls(data[2], data[3])

        elif cat == 'states':
            field_names = self._fields_cache[cls]
            if isinstance(data[2], dict):
                kwargs = {name: from_raw(data[2][name]) for name in field_names if name in data[2]}
            else:
                kwargs = {name: from_raw(data[i + 2]) for i, name in enumerate(field_names)}
            return cls(**kwargs)

        raise TypeError(f"Unknown category:  {cat}")

    def get_stats(self) -> dict:
        """Return statistics about registered types."""
        return {
            'total_types':  len(self._class_from_id),
            'dataclasses': sum(1 for c in self._category.values() if c == 'dataclass'),
            'enums': sum(1 for c in self._category. values() if c == 'enum'),
            'list_wrappers': sum(1 for c in self._category.values() if c == 'list'),
            'dict_wrappers': sum(1 for c in self._category.values() if c == 'dict'),
            'preloaded': self._preloaded,
        }