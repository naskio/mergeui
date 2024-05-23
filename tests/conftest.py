import pytest
from pathlib import Path
from mergeui import core, repositories, services
from mergeui.core.dependencies import get_settings, get_graph_repository, get_model_repository, get_db_connection, \
    get_model_service


@pytest.fixture(scope="session", autouse=True)
def settings() -> 'core.settings.Settings':
    return get_settings()


@pytest.fixture(scope="session")
def graph_json_path(settings) -> Path:
    return settings.project_dir / "tests/test_data/graph.json"


@pytest.fixture(scope="session")
def db_conn(graph_json_path) -> 'core.db.DatabaseConnection':
    db_conn = get_db_connection()
    db_conn.setup()
    db_conn.populate_from_json_file(graph_json_path)
    yield db_conn
    db_conn.reset()


@pytest.fixture(scope="session")
def graph_repository(db_conn) -> 'repositories.GraphRepository':
    return get_graph_repository()


@pytest.fixture(scope="session")
def model_repository(settings, db_conn) -> 'repositories.ModelRepository':
    repo = get_model_repository()
    yield repo
    if settings.memgraph_text_search_disabled:
        repo.drop_text_search_index()


@pytest.fixture(scope="session")
def model_service(db_conn, graph_repository, model_repository) -> 'services.ModelService':
    return get_model_service()
