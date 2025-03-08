import inspect
from datetime import datetime, timedelta, UTC
from typing import get_args
from typing import get_origin


# Helper functions for parsing a mapped value


def unix_to_datetime(timestamp):
    if timestamp is None:
        return None
# TODO this is not gonna work in a few years
    if len(str(timestamp)) == 10:
        return datetime.fromtimestamp(int(timestamp), UTC)
    elif len(str(timestamp)) == 13:
        return datetime.fromtimestamp(int(timestamp)/1000, UTC)


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