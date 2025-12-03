import inspect
import os
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import Optional

MS_PER_SECOND = 1000

# Helper functions for parsing a mapped value


def unix_to_datetime(timestamp):
    if timestamp is None:
        return None
# TODO this is not gonna work in a few years
    if len(str(timestamp)) == 10:
        return datetime.fromtimestamp(int(timestamp), UTC)
    elif len(str(timestamp)) == 13:
        return datetime.fromtimestamp(int(timestamp)/1000, UTC)

def unix_ms_to_datetime(timestamp_ms: int) -> Optional[datetime]:
    if timestamp_ms is None:
        return None
    return datetime.fromtimestamp(float(timestamp_ms) / MS_PER_SECOND, tz=UTC)

def datetime_to_unix_ms(dt: datetime) -> int:
    """
    Convert datetime to milliseconds timestamp.

    Args:
        dt: Datetime to convert

    Returns:
        Timestamp in milliseconds
    """
    return int(dt.timestamp() * MS_PER_SECOND)

def safe_issubclass(obj, cls):
    """
    Safely check if `obj` is a subclass of `cls`.

    Returns `True` if `obj` is a class and a subclass of `cls`, `False` if `obj` is not a class
    (e.g., a typing construct like List[int]), and raises an error if `cls` is not a class or
    tuple of classes, consistent with built-in `issubclass` behavior.

    Args:
        obj: The object to check.
        cls: The class or tuple of classes to check against.

    Returns:
        bool: `True` if `obj` is a subclass of `cls`, `False` otherwise.

    Raises:
        TypeError: If `cls` is not a class or tuple of classes.
    """
    if inspect.isclass(obj):
        return issubclass(obj, cls)
    else:
        return False

def is_primitive(obj):
    """Check if obj is a primitive or a list/dict containing only primitives."""
    if isinstance(obj, (int, float, bool, str, bytes)):
        return True
    return False

def create_new_file(file_path: Path):
    parent = os.path.dirname(file_path)
    if parent:
        os.makedirs(parent, exist_ok=True)
