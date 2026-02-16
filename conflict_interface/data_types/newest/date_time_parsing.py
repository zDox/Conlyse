from datetime import UTC

from .custom_types import DateTimeMillisecondsInt
from .custom_types import DateTimeMillisecondsStr
from .custom_types import DateTimeSecondsInt
from .custom_types import DateTimeSecondsStr
from .custom_types import TimeDeltaMillisecondsInt
from .custom_types import TimeDeltaMillisecondsStr
from .custom_types import TimeDeltaSecondsInt
from .custom_types import TimeDeltaSecondsStr
from .version import VERSION
from conflict_interface.game_object.decorators import custom_parser

@custom_parser(type_=DateTimeMillisecondsInt, version=VERSION)
@custom_parser(type_=DateTimeMillisecondsStr, version=VERSION)
def parse_date_time_milliseconds(json_obj):
    if len(str(json_obj)) < 13 and str(json_obj) != "0":
        raise ValueError(f"Expected int with at least 13 digits, got {len(str(json_obj))} digits {json_obj}")
    if type(json_obj) is str:
        return DateTimeMillisecondsStr.fromtimestamp(int(json_obj) / 1000, UTC)
    elif type(json_obj) is int:
        return DateTimeMillisecondsInt.fromtimestamp(int(json_obj) / 1000, UTC)
    else:
        raise ValueError(f"Expected int or str time, got {type(json_obj)}")

@custom_parser(type_=TimeDeltaMillisecondsInt, version=VERSION)
@custom_parser(type_=TimeDeltaMillisecondsStr, version=VERSION)
def parse_time_delta_milliseconds(json_obj):
    if type(json_obj) is str:
        return TimeDeltaMillisecondsStr(seconds=int(json_obj) / 1000)
    elif type(json_obj) is int:
        return TimeDeltaMillisecondsInt(seconds=int(json_obj) / 1000)
    else:
        raise ValueError(f"Expected int or str time, got {type(json_obj)}")

@custom_parser(type_=DateTimeSecondsInt, version=VERSION)
@custom_parser(type_=DateTimeSecondsStr, version=VERSION)
def parse_date_time_seconds(json_obj):
    if len(str(json_obj)) != 10 and str(json_obj) != "0":
        raise ValueError(f"Expected int with 10 digits, got {len(str(json_obj))} digits {json_obj}")
    if type(json_obj) is str:
        return DateTimeSecondsStr.fromtimestamp(int(json_obj), UTC)
    elif type(json_obj) is int:
        return DateTimeSecondsInt.fromtimestamp(int(json_obj), UTC)
    else:
        raise ValueError(f"Expected int or str time, got {type(json_obj)}")

@custom_parser(type_=TimeDeltaSecondsInt, version=VERSION)
@custom_parser(type_=TimeDeltaSecondsStr, version=VERSION)
def parse_time_delta_seconds(json_obj):
    if type(json_obj) is str:
        return TimeDeltaSecondsStr(seconds=int(json_obj))
    elif type(json_obj) is int:
        return TimeDeltaSecondsInt(seconds=int(json_obj))
    else:
        raise ValueError(f"Expected int or str time, got {type(json_obj)}")


"""
DATETIME_MAPPING = {
    DateTimeMillisecondsInt: parse_date_time_milliseconds,
    DateTimeMillisecondsStr: parse_date_time_milliseconds,
    TimeDeltaMillisecondsInt: parse_time_delta_milliseconds,
    TimeDeltaMillisecondsStr: parse_time_delta_milliseconds,
    DateTimeSecondsInt: parse_date_time_seconds,
    DateTimeSecondsStr: parse_date_time_seconds,
    TimeDeltaSecondsInt: parse_time_delta_seconds,
    TimeDeltaSecondsStr: parse_time_delta_seconds,
}"""