from datetime import datetime, timedelta, UTC


# Helper functions for parsing a mapped value


def timestamp_to_datetime(timestamp):
    return datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S") \
            if timestamp else None


def unixtimestamp_to_datetime(timestamp):
    if timestamp is None:
        return None

    if len(str(timestamp)) == 10:
        return datetime.fromtimestamp(int(timestamp), UTC)
    elif len(str(timestamp)) == 13:
        return datetime.fromtimestamp(int(timestamp)/1000, UTC)


def seconds_to_timedelta(seconds):
    if seconds is None:
        return None
    else:
        return timedelta(seconds=seconds)


def milliseconds_to_timedelta(milliseconds):
    if milliseconds is None:
        return None
    else:
        return timedelta(milliseconds=milliseconds)
