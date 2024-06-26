import functools as fts
from mergeui.core.settings import Settings
from mergeui.core.db import DatabaseConnection
from mergeui.repositories import GraphRepository, ModelRepository
from mergeui.services import ModelService
from mergeui.utils import set_env_var
from mergeui.utils.logging import set_logger_level


@fts.cache
def get_settings() -> Settings:
    settings = Settings()
    set_logger_level(settings.logging_level)
    set_env_var('HF_HUB_ENABLE_HF_TRANSFER', settings.hf_hub_enable_hf_transfer)
    return settings


@fts.cache
def get_db_connection():
    settings = get_settings()
    return DatabaseConnection(settings)


@fts.cache
def get_graph_repository() -> GraphRepository:
    return GraphRepository(get_db_connection())


@fts.cache
def get_model_repository() -> ModelRepository:
    repo = ModelRepository(get_db_connection())
    if get_settings().memgraph_text_search_disabled:
        repo.create_text_search_index(False)
    return repo


@fts.cache
def get_model_service() -> ModelService:
    return ModelService(graph_repository=get_graph_repository(), model_repository=get_model_repository())
