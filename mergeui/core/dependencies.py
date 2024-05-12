from functools import lru_cache
import core.settings
from core.db import DatabaseConnection
from repositories import GraphRepository, ModelRepository
from services import ModelService


@lru_cache
def get_settings() -> 'core.settings.Settings':
    return core.settings.settings


@lru_cache
def get_db_connection():
    settings = get_settings()
    return DatabaseConnection(settings)


@lru_cache
def get_graph_repository() -> GraphRepository:
    db_conn = get_db_connection()
    return GraphRepository(db_conn)


@lru_cache
def get_model_repository() -> ModelRepository:
    db_conn = get_db_connection()
    return ModelRepository(db_conn)


@lru_cache
def get_model_service() -> ModelService:
    gr = get_graph_repository()
    mr = get_model_repository()
    return ModelService(graph_repository=gr, model_repository=mr)
