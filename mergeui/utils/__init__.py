import datetime as dt
import typing as t
import yaml
from numerize import numerize


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


def format_large_number(n_: int) -> t.Optional[str]:
    if n_ is not None:
        return numerize.numerize(n_)


def filter_none(d: list) -> list:
    return [x for x in d if x is not None]


def parse_yaml(yaml_str: str) -> list[t.Union[dict, list]]:
    try:
        docs = list(yaml.safe_load_all(yaml_str))  # support multi-document yaml
        return [doc for doc in docs if doc is not None]
    except yaml.YAMLError:
        return []
