import pytest
import datetime as dt
from pathlib import Path
from utils import parse_yaml, filter_none, format_large_number, naive_to_aware_dt, aware_to_naive_dt, pretty_format_dt, \
    parse_iso_dt, iso_format_dt


@pytest.fixture
def yaml_single_doc_path(settings) -> Path:
    return settings.project_dir / 'tests/test_data/mergekit_config.yml'


@pytest.fixture
def yaml_multi_docs_path(settings) -> Path:
    return settings.project_dir / 'tests/test_data/mergekit_config__multi_docs.yml'


@pytest.fixture
def naive_dt() -> dt.datetime:
    return dt.datetime(2021, 10, 1, 12, 9, 30, 12345)


@pytest.fixture
def utc_dt() -> dt.datetime:
    return dt.datetime(2021, 10, 1, 12, 9, 30, 12345, dt.timezone.utc)


@pytest.fixture
def no_utc_dt() -> dt.datetime:
    return dt.datetime(2021, 10, 1, 13, 9, 30, 12345, dt.timezone(dt.timedelta(hours=1)))


@pytest.fixture
def pretty_dt() -> str:
    return "2021-10-01 12:09:30"


@pytest.fixture
def iso_dt() -> str:
    return "2021-10-01T12:09:30.012345Z"


def test_parse_yaml(yaml_single_doc_path, yaml_multi_docs_path):
    yaml_docs = parse_yaml(yaml_single_doc_path.read_text())
    assert yaml_docs is not None
    assert len(yaml_docs) == 1
    assert all([doc is not None for doc in yaml_docs])
    yaml_docs = parse_yaml(yaml_multi_docs_path.read_text())
    assert yaml_docs is not None
    assert len(yaml_docs) > 1
    assert all([doc is not None for doc in yaml_docs])


def test_filter_none():
    assert filter_none([1, 2, None, 3, None]) == [1, 2, 3]
    assert filter_none({1: 1, 2: 2, 3: None, 4: None}) == {1: 1, 2: 2}
    assert filter_none({1: 1, 2: 2, 3: 3, 4: 4}) == {1: 1, 2: 2, 3: 3, 4: 4}
    assert filter_none([1, 2, 3, 4]) == [1, 2, 3, 4]
    assert filter_none([]) == []
    assert filter_none({}) == {}
    assert filter_none(None) is None
    assert filter_none(1) == 1
    assert filter_none("1") == "1"
    assert filter_none(True) is True
    assert filter_none(False) is False
    assert filter_none(0) == 0
    assert filter_none(0.0) == 0.0
    assert filter_none(0.0j) == 0.0j
    assert filter_none(0j) == 0j


def test_format_large_number():
    assert format_large_number(9) == '9'
    assert format_large_number(958) == '958'
    assert format_large_number(1256) == '1.26K'
    assert format_large_number(1312000) == '1.31M'
    assert format_large_number(1000000000) == '1B'
    assert format_large_number(1000000000000) == '1T'
    assert format_large_number(1000000000000000) == '1000000000000000'


def test_naive_to_aware_dt(naive_dt, utc_dt, no_utc_dt):
    assert naive_to_aware_dt(naive_dt) == utc_dt
    assert naive_to_aware_dt(utc_dt) == utc_dt
    assert naive_to_aware_dt(no_utc_dt) == no_utc_dt


def test_aware_to_naive_dt(naive_dt, utc_dt, no_utc_dt):
    assert aware_to_naive_dt(naive_dt) == naive_dt
    assert aware_to_naive_dt(utc_dt) == naive_dt
    assert aware_to_naive_dt(no_utc_dt) == naive_dt


def test_pretty_format_dt(naive_dt, utc_dt, no_utc_dt, pretty_dt):
    assert pretty_format_dt(None) is None
    assert pretty_format_dt(naive_dt) == pretty_dt
    assert pretty_format_dt(utc_dt) == pretty_dt
    assert pretty_format_dt(no_utc_dt) == pretty_dt


def test_parse_iso_dt(utc_dt, iso_dt, naive_dt):
    parsed_dt = parse_iso_dt(iso_dt)
    assert parsed_dt != naive_dt
    assert parsed_dt.tzinfo is dt.timezone.utc
    assert parsed_dt == utc_dt


def test_iso_format_dt(utc_dt, iso_dt, naive_dt):
    assert iso_format_dt(None) is None
    assert iso_format_dt(naive_dt) == iso_dt
    assert iso_format_dt(utc_dt) == iso_dt
