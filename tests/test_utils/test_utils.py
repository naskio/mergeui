import pytest
from pathlib import Path
from core.settings import Settings
from utils import parse_yaml

settings = Settings()


@pytest.fixture(scope="session")
def mergekit_config_path() -> Path:
    return settings.project_dir / 'tests/test_data/single_document.yml'


@pytest.fixture(scope="session")
def mergekit_config_path__multi_docs() -> Path:
    return settings.project_dir / 'tests/test_data/multi_documents.yml'


@pytest.fixture(scope="session")
def mergekit_moe_config_path() -> Path:
    return settings.project_dir / 'tests/test_data/mergekit_moe_config.yml'


def test_parse_yaml(mergekit_config_path, mergekit_config_path__multi_docs):
    yaml_docs = parse_yaml(mergekit_config_path.read_text())
    assert yaml_docs is not None
    assert len(yaml_docs) == 1
    assert all([doc is not None for doc in yaml_docs])
    yaml_docs = parse_yaml(mergekit_config_path__multi_docs.read_text())
    assert yaml_docs is not None
    assert len(yaml_docs) == 2
    assert all([doc is not None for doc in yaml_docs])
