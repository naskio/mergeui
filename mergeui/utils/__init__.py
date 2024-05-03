import datetime as dt


def parse_datetime(t_str: str) -> dt.datetime:
    return dt.datetime.strptime(t_str, "%Y-%m-%dT%H:%M:%S.%fZ")


def format_datetime(t: dt.datetime) -> str:
    # return f"{t.isoformat(timespec='milliseconds')}Z"
    return f"{t.strftime('%Y-%m-%dT%H:%M:%S')}.000Z"
