import pytest
import sys
from loguru import logger
import fastapi as fa
from fastapi.testclient import TestClient
from core.db import DatabaseConnection, Settings
from repositories.graph import GraphRepository
from services.models import ModelService
from web.api import router as api_router

logger.remove()
logger.add(sink=sys.stderr, level='INFO')


class TestApi:
    @pytest.fixture(scope="class")
    def client(self) -> TestClient:
        app = fa.FastAPI()
        app.include_router(api_router, prefix="/api")
        return TestClient(app)

    @classmethod
    def setup_class(cls):
        cls.settings = Settings()
        cls.db_conn = DatabaseConnection(cls.settings)
        # cls.teardown_class()
        cls.db_conn.setup()
        cls.service = ModelService(GraphRepository(cls.db_conn))
        cls.db_conn.populate_from_json(cls.settings.project_dir / "tests/test_data/graph.json")

    @classmethod
    def teardown_class(cls):
        cls.db_conn.reset()

    def test_list_models(self, client):
        response = client.get("/api/models", params={
            "query": "Q-bert",
            "columns": ["id", "name", "license", "likes"],
            "sort_by": "most likes",
        })
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is True
        assert isinstance(data.get("data"), list)
        assert len(data.get("data")) > 0

    def test_model_lineage(self, client):
        response = client.get("/api/model_lineage", params={"id": "Q-bert/MetaMath-Cybertron-Starling"})
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is True
        assert isinstance(data.get("data"), dict)
        assert "nodes" in data.get("data")
        assert "relationships" in data.get("data")
        assert len(data.get("data").get("nodes")) == 5
        assert len(data.get("data").get("relationships")) == 7

    def test_list_models__columns(self, client):
        response = client.get("/api/models", params={
            "query": "MistralForCausalLM",
            "columns": ["id", "name", "license"],
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
