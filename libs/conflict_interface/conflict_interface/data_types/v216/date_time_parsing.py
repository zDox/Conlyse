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
from conflict_interface.game_object.game_object_parse_json import JsonParser


def parse_date_time_milliseconds(json_obj):
    if len(str(json_obj)) < 13 and str(json_obj) != "0":
        raise ValueError(f"Expected int with at least 13 digits, got {len(str(json_obj))} digits {json_obj}")
    if type(json_obj) is str:
        return DateTimeMillisecondsStr.fromtimestamp(int(json_obj) / 1000, UTC)
    elif type(json_obj) is int:
        return DateTimeMillisecondsInt.fromtimestamp(int(json_obj) / 1000, UTC)
    else:
        raise ValueError(f"Expected int or str time, got {type(json_obj)}")

def parse_time_delta_milliseconds(json_obj):
    if type(json_obj) is str:
        return TimeDeltaMillisecondsStr(seconds=int(json_obj) / 1000)
    elif type(json_obj) is int:
        return TimeDeltaMillisecondsInt(seconds=int(json_obj) / 1000)
    else:
        raise ValueError(f"Expected int or str time, got {type(json_obj)}")

def parse_date_time_seconds(json_obj):
    if len(str(json_obj)) != 10 and str(json_obj) != "0":
        raise ValueError(f"Expected int with 10 digits, got {len(str(json_obj))} digits {json_obj}")
    if type(json_obj) is str:
        return DateTimeSecondsStr.fromtimestamp(int(json_obj), UTC)
    elif type(json_obj) is int:
        return DateTimeSecondsInt.fromtimestamp(int(json_obj), UTC)
    else:
        raise ValueError(f"Expected int or str time, got {type(json_obj)}")

def parse_time_delta_seconds(json_obj):
    if type(json_obj) is str:
        return TimeDeltaSecondsStr(seconds=int(json_obj))
    elif type(json_obj) is int:
        return TimeDeltaSecondsInt(seconds=int(json_obj))
    else:
        raise ValueError(f"Expected int or str time, got {type(json_obj)}")

JsonParser.register_custom_parser(TimeDeltaSecondsStr, VERSION, parse_time_delta_seconds)
JsonParser.register_custom_parser(TimeDeltaSecondsInt, VERSION, parse_time_delta_seconds)
JsonParser.register_custom_parser(TimeDeltaMillisecondsStr, VERSION, parse_time_delta_milliseconds)
JsonParser.register_custom_parser(TimeDeltaMillisecondsInt, VERSION, parse_time_delta_milliseconds)
JsonParser.register_custom_parser(DateTimeSecondsStr, VERSION, parse_date_time_seconds)
JsonParser.register_custom_parser(DateTimeSecondsInt, VERSION, parse_date_time_seconds)
JsonParser.register_custom_parser(DateTimeMillisecondsStr, VERSION, parse_date_time_milliseconds)
JsonParser.register_custom_parser(DateTimeMillisecondsInt, VERSION, parse_date_time_milliseconds)
