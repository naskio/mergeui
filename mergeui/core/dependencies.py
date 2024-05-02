import fastapi as fa
from functools import lru_cache
from core.settings import Settings
from core.db import DatabaseConnection
from repositories.graph import GraphRepository
from services.models import ModelService


@lru_cache
def get_settings():
    return Settings()


@lru_cache
async def get_db_connection(settings=fa.Depends(get_settings)):
    return DatabaseConnection(settings)


def get_graph_repository(db_conn=fa.Depends(get_db_connection)) -> GraphRepository:
    return GraphRepository(db_conn)


def get_model_service(repository=fa.Depends(get_graph_repository)) -> ModelService:
    return ModelService(repository)
