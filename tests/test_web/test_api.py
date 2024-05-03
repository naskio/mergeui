import pytest
import fastapi as fa
from fastapi.testclient import TestClient
from web.api import router as api_router


@pytest.fixture
def client() -> TestClient:
    app = fa.FastAPI()
    app.include_router(api_router, prefix="/api")
    return TestClient(app)


def test_list_models(client):
    response = client.get("/api/models", params={
        "query": "Q-bert",
        "columns": ["id", "name", "license", "likes"],
        "sort_by": "most likes",
    })
    assert response.status_code == 200
    data = response.json()
    print(data)
    assert data.get("success") is True
    assert isinstance(data.get("data"), list)
