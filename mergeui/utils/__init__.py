import typing as t
from loguru import logger
import datetime as dt
import re
import yaml
import yaml.scanner
from numerize import numerize


def naive_to_aware_dt(t_: dt.datetime) -> dt.datetime:
    """Force datetime to be an aware datetime in UTC timezone."""
    if t_.tzinfo is None:
        t_ = t_.replace(tzinfo=dt.timezone.utc)  # otherwise will take local timezone
    return t_.astimezone(dt.timezone.utc)


def aware_to_naive_dt(t_: dt.datetime) -> dt.datetime:
    """Convert aware datetime to naive datetime."""
    if t_.tzinfo is None:
        return t_
    t_ = naive_to_aware_dt(t_)  # make sure it's in UTC timezone
    return t_.replace(tzinfo=None)


def pretty_format_dt(t_: t.Optional[dt.datetime]) -> t.Optional[str]:
    """Format datetime to human-readable string."""
    if t_ is not None:
        t_ = naive_to_aware_dt(t_)
        return t_.strftime("%Y-%m-%d %H:%M:%S")


def parse_iso_dt(t_str: t.Optional[str]) -> t.Optional[dt.datetime]:
    """Parse ISO datetime string (2024-01-25T11:44:11.000Z) to aware datetime object in UTC timezone."""
    if t_str is not None:
        t_str = t_str.replace("Z", "")
        return naive_to_aware_dt(dt.datetime.strptime(t_str, "%Y-%m-%dT%H:%M:%S.%f"))


def iso_format_dt(t_: t.Optional[dt.datetime]) -> t.Optional[str]:
    """Format aware datetime in UTC timezone to ISO datetime string."""
    if t_ is not None:
        t_ = naive_to_aware_dt(t_)
        return f"{t_.strftime('%Y-%m-%dT%H:%M:%S.%f')}Z"


def pretty_format_int(n_: t.Optional[int]) -> t.Optional[str]:
    """Format large number to human-readable string."""
    if n_ is not None:
        return numerize.numerize(n_)


def pretty_format_float(f_: t.Optional[float], suffix: str = "", as_float: bool = False) \
        -> t.Optional[t.Union[str, float]]:
    """Format float as rounded percentage (0.24123 => 24.12)."""
    if f_ is not None:
        res = round(f_ * 100, 2)
        if as_float:
            return res
        return f"{res}{suffix}"


def pretty_format_description(description: t.Optional[str], private: bool, is_valid_id: bool) -> t.Optional[str]:
    """Format model description for visualisation."""
    if not description:
        if not is_valid_id:
            return "Not available on HuggingFace and seems to be a local (#) model."
        if private:
            return "Not available on HuggingFace and seems to be a private or deleted model."
    return description


def is_valid_repo_id(repo_id: str) -> bool:
    """Check if str a valid repo_id with namespace/repo_name format."""
    return bool(re.match(r"^[-.\w]+/[-.\w]+$", repo_id))


def titlify(s: t.Optional[str]) -> t.Optional[str]:
    """Convert snake_case string to title case."""
    if not s:
        return s
    if s[0].isupper():
        return s
    return s.replace("_", " ").title()


def filter_none(d: t.Union[list, dict, t.Any]) -> t.Union[list, dict, t.Any]:
    """Filter out None values from a list or dictionary."""
    if isinstance(d, dict):
        return {k: v for k, v in d.items() if v is not None}
    elif isinstance(d, list):
        return [x for x in d if x is not None]
    else:
        return d


def parse_yaml(yaml_str: str) -> list[t.Union[dict, list]]:
    """Parse YAML string to list of dictionaries (support also multi-documents yaml string)."""
    try:
        docs = list(yaml.safe_load_all(yaml_str))  # support multi-document yaml
        return [doc for doc in docs if doc is not None]
    except (yaml.YAMLError, yaml.scanner.ScannerError):
        return []


def custom_serializer(obj):
    """Custom JSON serializer for dt.datetime."""
    if isinstance(obj, dt.datetime):
        return iso_format_dt(obj)
    raise TypeError(f"Type {type(obj)} not serializable")


def log_progress(count: int, total: int, step: int = 5) -> None:
    """Log progress percentage."""
    count = count + 1  # start from 1
    if total > 100 * step:
        if count % (total // 100 * step) == 0:
            logger.debug(f"{(count / total) * 100:.2f}%")


def format_duration(start: float, end: float) -> str:
    """Format duration from start to end time in seconds since epoch."""
    duration = end - start
    hours, remainder = divmod(duration, 3600.0)
    minutes, seconds = divmod(remainder, 60.0)
    hours = int(hours)
    minutes = int(minutes)
    seconds = round(seconds, 3)
    return f"{hours:02}:{minutes:02}:{seconds:0>6.3f} (hh:mm:ss.sss)"


def escaped(d: t.Optional[t.Union[dict, str]]) -> t.Optional[t.Union[dict, str]]:
    """Escape value for gqlalchemy"""
    replacements = {
        "\\": "\\\\",
        "'": "\\'",
        '"': '\\"',
    }
    if isinstance(d, str):
        for k, v in replacements.items():
            d = d.replace(k, v)
        return d
    if isinstance(d, dict):
        return {k: escaped(v) for k, v in d.items()}
    return d
