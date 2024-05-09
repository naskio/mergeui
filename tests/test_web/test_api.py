import pytest
import fastapi as fa
from fastapi.testclient import TestClient
from web.api import router as api_router


@pytest.fixture(scope="module")
def api_client(db_conn) -> TestClient:
    app = fa.FastAPI()
    app.include_router(api_router, prefix="/api")
    return TestClient(app)


def test_list_models(api_client):
    response = api_client.get("/api/models", params={
        "query": "Q-bert",
        "display_columns": ["id", "name", "license", "likes"],
        "sort_by": "most likes",
    })
    assert response.status_code == 200
    data = response.json()
    assert data.get("success") is True
    assert isinstance(data.get("data"), list)
    assert len(data.get("data")) > 0
    assert 'id' in data.get("data")[0]
    assert 'name' in data.get("data")[0]
    assert 'downloads' not in data.get("data")[0]


def test_list_models__columns(api_client):
    response = api_client.get("/api/models", params={
        "query": "MistralForCausalLM",
        "display_columns": ["id", "name", "license"],
    })
    assert response.status_code == 200
    data = response.json()
    assert data.get("success") is True
    result = data.get("data")
    assert len(result) > 0
    assert 'id' in result[0]
    assert 'name' in result[0]
    assert 'license' in result[0]
    assert 'architecture' not in result[0]
    assert 'indexed' not in result[0]


def test_model_lineage(api_client):
    response = api_client.get("/api/model_lineage", params={"id": "Q-bert/MetaMath-Cybertron-Starling"})
    assert response.status_code == 200
    data = response.json()
    assert data.get("success") is True
    assert isinstance(data.get("data"), dict)
    assert "nodes" in data.get("data")
    assert "relationships" in data.get("data")
    assert len(data.get("data").get("nodes")) == 5
    assert len(data.get("data").get("relationships")) == 7
    node = data.get("data").get("nodes")[0]
    assert "id" in node
    assert "name" in node
    rel = data.get("data").get("relationships")[0]
    assert "source" in rel
    assert "method" in rel
