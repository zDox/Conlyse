import importlib
import sys
from dataclasses import fields

_FIELDS_CACHE: dict[type, tuple] = {}

def _get_fields(cls: type) -> tuple:
    if cls not in _FIELDS_CACHE:
        _FIELDS_CACHE[cls] = tuple(f for f in fields(cls) if f.name != 'game')
    return _FIELDS_CACHE[cls]

def _get_class_path(cls: type) -> str:
    return f"{cls.__module__}.{cls.__name__}"

