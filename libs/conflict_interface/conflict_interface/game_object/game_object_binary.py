from dataclasses import fields
from datetime import UTC
from enum import Enum
from logging import getLogger
from typing import Any
import hashlib
import re

import msgspec

from conflict_interface.game_object.game_object import GameObject

logger = getLogger()

class SerializationCategory(Enum):
    DATACLASS = 1
    ENUM = 2
    LIST = 3
    DICT = 4
    DATETIME = 5
    TIMEDELTA = 6
    POINT = 7
    GAME_STATE = 8
    STATIC_MAP_DATA = 9

def stable_type_id(cls):
    normalized = re.sub(r'\.(newest|v\d+)\.', '.', cls.__module__)
    s = f"{normalized}.{cls.__qualname__}".encode()
    return int.from_bytes(hashlib.sha256(s).digest()[:4], "little")


def get_mapping(cls):
    if hasattr(cls, 'get_mapping'):
        return cls.get_mapping()
    elif hasattr(cls, 'MAPPING'):
        return cls.MAPPING
    else:
        return {f.name: None for f in fields(cls)}

class GameObjectSerializer:
    _PRIMITIVES = frozenset({int, float, str, bool, type(None)})

    _CLASS_FROM_ID: dict[int, dict[int, type]] = {} # version -> id -> class
    _ID_FROM_CLASS: dict[int, dict[type, int]] = {} # version -> class -> id
    _CATEGORY: dict[int, dict[type, SerializationCategory]] = {} # version -> class -> category

    _FIELDS_CACHE: dict[int, dict[type, tuple[str, ...]]] = {} # version -> class -> tuple[fields]

    # Marker to distinguish [type_id, ... ] from plain lists
    _TYPE_MARKER = -1

    def __init__(self, version: int):
        self._encoder = msgspec.msgpack.Encoder()
        self._decoder = msgspec.msgpack.Decoder()
        self.version:int = version

        self._class_from_id = self._CLASS_FROM_ID.get(self.version, {})
        self._id_from_class = self._ID_FROM_CLASS.get(self.version, {})
        self._category = self._CATEGORY.get(self.version, {})
        self._fields = self._FIELDS_CACHE.get(self.version, {})

        self._class_from_id.update(self._CLASS_FROM_ID.get(-1, {}))
        self._id_from_class.update(self._ID_FROM_CLASS.get(-1, {}))
        self._category.update(self._CATEGORY.get(-1, {}))
        self._fields.update(self._FIELDS_CACHE.get(-1, {}))


        
    @classmethod
    def register(cls, version: int, obj: type, category: SerializationCategory):
        """Register a type with its category."""
        type_id = stable_type_id(obj)
        cls._CLASS_FROM_ID.setdefault(version, {})
        cls._ID_FROM_CLASS.setdefault(version, {})
        cls._CATEGORY.setdefault(version, {})

        cls._CLASS_FROM_ID[version][type_id] = obj
        cls._ID_FROM_CLASS[version][obj] = type_id
        cls._CATEGORY[version][obj] = category

        if category in (SerializationCategory.DATACLASS, SerializationCategory.GAME_STATE, SerializationCategory.STATIC_MAP_DATA):
            mapping = get_mapping(obj)
            cls._FIELDS_CACHE.setdefault(version, {})
            cls._FIELDS_CACHE[version][obj] = tuple(mapping.keys())


    def serialize(self, obj: Any) -> bytes:
        raw = self._to_raw(obj)
        obj =  self._encoder.encode(raw)
        return obj

    def serialize_game_object(self, obj: GameObject) -> bytes:
        game = obj.game
        if game is not None:
            GameObject.set_game_recursive(obj, None)
        raw = self._to_raw(obj)
        obj = self._encoder.encode(raw)
        if game is not None:
            GameObject.set_game_recursive(obj, game)
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

        type_id = self._id_from_class[t]
        cat = self._category[t]



        if cat == SerializationCategory.DATACLASS or cat == SerializationCategory.GAME_STATE or cat == SerializationCategory.STATIC_MAP_DATA:
            field_names: tuple[str,  ...] = self._fields[t]
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
            primitives = self._PRIMITIVES
            return {
                (k if type(k) in primitives else from_raw(k)):
                    (v if type(v) in primitives else from_raw(v))
                for k, v in data["__dict__"]
            }


        if t is list:
            # Check if it's a registered type:  [MARKER, type_id, ...]
            if len(data) >= 2 and data[0] == self._TYPE_MARKER:
                return self._from_raw_registered(data)
            else:
                # Plain list
                from_raw = self._from_raw
                primitives = self._PRIMITIVES
                return [v if type(v) in primitives else from_raw(v) for v in data]

        raise TypeError(f"Cannot deserialize:  {type(data)} \n {str(data)[:1000]}")

    def _from_raw_registered(self, data):
        """Handle deserialization of registered types."""
        type_id = data[1]
        cls = self._class_from_id.get(type_id)
        if cls is None:
            registered = sorted(self._class_from_id.keys())
            raise KeyError(
                f"Unknown type_id {type_id} ({type_id:#010x}) for serializer version {self.version}. "
                f"The replay was likely recorded with a different schema version. "
                f"Registered IDs ({len(registered)}): {registered[:10]}{'...' if len(registered) > 10 else ''}"
            )
        cat = self._category[cls]
        from_raw = self._from_raw
        # Avoid a full recursive _from_raw call (frame setup + branch tree)
        # for the common case of an already-primitive field value.
        primitives = self._PRIMITIVES

        if cat in (SerializationCategory.DATACLASS, SerializationCategory.GAME_STATE, SerializationCategory.STATIC_MAP_DATA):
            field_names = self._fields[cls]
            kwargs = {}
            for i, name in enumerate(field_names):
                v = data[i + 2]
                kwargs[name] = v if type(v) in primitives else from_raw(v)
            instance = cls(**kwargs)
            instance.game = None
            return instance

        elif cat == SerializationCategory.LIST:
            return cls([v if type(v) in primitives else from_raw(v) for v in data[2]])

        elif cat == SerializationCategory.DICT:
            return cls({
                (pair[0] if type(pair[0]) in primitives else from_raw(pair[0])):
                    (pair[1] if type(pair[1]) in primitives else from_raw(pair[1]))
                for pair in data[2]
            })

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
            'total_types':  len(self._class_from_id),
            'dataclasses': sum(1 for c in self._category.values() if c in (SerializationCategory.DATACLASS, SerializationCategory.STATIC_MAP_DATA, SerializationCategory.GAME_STATE)),
            'enums': sum(1 for c in self._category. values() if c == SerializationCategory.ENUM),
            'list_wrappers': sum(1 for c in self._category.values() if c == SerializationCategory.LIST),
            'dict_wrappers': sum(1 for c in self._category.values() if c == SerializationCategory.DICT)
        }


# Hardcoded expected IDs for a cross-section of types (GAME_STATE, DATACLASS, ENUM).
# These are derived from normalized module paths so they are version-alias-independent.
# If this check fails at startup it means Nuitka (or something else) has rewritten
# __module__ or __qualname__, which would silently corrupt binary serialization.
_EXPECTED_IDS: dict[str, int] = {
    "conflict_interface.data_types.game_state.game_state.GameState":          3249973404,
    "conflict_interface.data_types.game_state.game_state.States":              975817546,
    "conflict_interface.data_types.player_state.player_state.PlayerState":     692747530,
    "conflict_interface.data_types.army_state.army_state.ArmyState":          3439915012,
    "conflict_interface.data_types.common.enums.region_type.RegionType":      3841545510,
}


def assert_stable_type_id_consistency() -> None:
    from conflict_interface.data_types.newest.game_state.game_state import GameState, States
    from conflict_interface.data_types.newest.player_state.player_state import PlayerState
    from conflict_interface.data_types.newest.army_state.army_state import ArmyState
    from conflict_interface.data_types.newest.common.enums.region_type import RegionType

    probes = [
        (GameState,   3249973404),
        (States,       975817546),
        (PlayerState,  692747530),
        (ArmyState,   3439915012),
        (RegionType,  3841545510),
    ]
    for cls, expected in probes:
        got = stable_type_id(cls)
        if got != expected:
            raise RuntimeError(
                f"stable_type_id mismatch for {cls.__qualname__}: "
                f"expected {expected:#010x}, got {got:#010x} "
                f"(__module__={cls.__module__!r}, __qualname__={cls.__qualname__!r}). "
                "Nuitka may have rewritten module paths — binary serialization is unsafe."
            )