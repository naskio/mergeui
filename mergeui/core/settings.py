import typing as t
from loguru import logger
import pydantic as pd
import pydantic_core as pdc
import pydantic_settings as pds
from pathlib import Path
from utils.logging import set_logger_level

PROJECT_DIR = Path(__file__).resolve().parent.parent.parent
logger.debug(f'PROJECT_DIR: {PROJECT_DIR}')


class Settings(pds.BaseSettings):
    model_config = pds.SettingsConfigDict(env_file=PROJECT_DIR / ".env", frozen=True, extra="ignore")
    project_dir: Path = PROJECT_DIR
    # UI settings
    project_name: str = "MergeUI"
    description: str = "UI for merged large language models"
    author: t.Optional[str] = None
    email: t.Optional[pd.EmailStr] = None
    repo_url: t.Optional[pd.AnyHttpUrl] = "https://github.com/naskio/mergeui"
    favicon_path: Path = PROJECT_DIR / 'static/brand/favicon.ico'
    # gradio
    gradio_app_disabled: bool = False
    gradio_load_custom_js: bool = True
    gradio_load_custom_css: bool = True
    # limit results
    max_graph_depth: t.Optional[int] = 3
    results_limit: t.Optional[int] = None
    # db connection
    database_url: t.Annotated[pdc.Url, pd.UrlConstraints(
        allowed_schemes=["bolt", "bolt+s", "neo4j", "neo4j+s"],
        default_host="localhost",
        default_port=7687,
    )] = "bolt://localhost:7687"  # use 7688 port for test db
    # redis connection
    redis_dsn: pd.RedisDsn = "redis://localhost:6379/0"
    # db settings
    text_index_name: str = "modelDocuments"
    memgraph_text_search_disabled: bool = True
    whoosh_case_sensitive: bool = False
    # logging
    logging_level: t.Literal['TRACE', 'DEBUG', 'INFO', 'SUCCESS', 'WARNING', 'ERROR', 'CRITICAL'] = "DEBUG"
    rq_logging_level: t.Optional[t.Literal['TRACE', 'DEBUG', 'INFO', 'SUCCESS', 'WARNING', 'ERROR', 'CRITICAL']] = None


settings = Settings()

set_logger_level(settings.logging_level)
