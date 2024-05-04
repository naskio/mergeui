import typing as t
import datetime as dt


def parse_iso_datetime_str(t_str: str) -> dt.datetime:
    return dt.datetime.strptime(t_str, "%Y-%m-%dT%H:%M:%S.%fZ")


def iso_format_datetime(t_: dt.datetime) -> t.Optional[str]:
    # return f"{t.isoformat(timespec='milliseconds')}Z"
    if not t_:
        return None
    return f"{t_.strftime('%Y-%m-%dT%H:%M:%S')}.000Z"


def format_datetime(t_: dt.datetime) -> t.Optional[str]:
    if not t_:
        return None
    return t_.strftime("%Y-%m-%d %H:%M:%S")
