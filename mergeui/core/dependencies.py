from functools import lru_cache
import core.settings
from core.db import DatabaseConnection
from repositories import GraphRepository
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
def get_model_service() -> ModelService:
    graph_repository = get_graph_repository()
    return ModelService(graph_repository)
