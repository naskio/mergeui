import pytest
from pathlib import Path
import core
import core.dependencies
import repositories
import services
from utils.logging import set_logger_level


@pytest.fixture(scope='session')
def mp_session():
    with pytest.MonkeyPatch.context() as mp:
        yield mp


@pytest.fixture(scope='session', autouse=True)
def setup_env(mp_session):
    mp_session.setenv("ENV", "test")
    mp_session.setattr(core.settings, "settings", core.settings.Settings(
        max_hops=None,
        max_results=None,
        database_url="bolt://localhost:7688",
        memgraph_text_search_disabled=False,
    ))


@pytest.fixture(scope="session", autouse=True)
def setup_logging():
    set_logger_level('ERROR')


@pytest.fixture(scope="session")
def settings() -> 'core.settings.Settings':
    return core.dependencies.get_settings()


@pytest.fixture(scope="session")
def graph_json_path(settings) -> Path:
    return settings.project_dir / "tests/test_data/graph.json"


@pytest.fixture(scope="session")
def db_conn(graph_json_path) -> 'core.db.DatabaseConnection':
    db_conn = core.dependencies.get_db_connection()
    db_conn.setup()
    db_conn.populate_from_json_file(graph_json_path)
    yield db_conn
    db_conn.reset()


@pytest.fixture(scope="session")
def graph_repository(db_conn) -> 'repositories.GraphRepository':
    return core.dependencies.get_graph_repository()


@pytest.fixture(scope="session")
def model_repository(db_conn) -> 'repositories.ModelRepository':
    return core.dependencies.get_model_repository()


@pytest.fixture(scope="session")
def model_service(graph_repository, model_repository) -> 'services.ModelService':
    return core.dependencies.get_model_service()
