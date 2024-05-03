import typing as t
from loguru import logger
import pydantic as pd
import pydantic_settings as pds
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent.parent
logger.debug(f'PROJECT_DIR: {PROJECT_DIR}')


class Settings(pds.BaseSettings):
    model_config = pds.SettingsConfigDict(env_file=PROJECT_DIR / ".env", frozen=True)
    project_dir: Path = PROJECT_DIR
    # UI settings
    app_name: str = "MergeUI"
    description: str = "UI for merged large language models"
    email: pd.EmailStr
    load_custom_js: bool = False
    load_custom_css: bool = False
    favicon_path: Path = PROJECT_DIR / 'static/brand/favicon.ico'
    max_graph_depth: int = 5
    disable_gradio_app: bool = False
    results_limit: t.Optional[int] = None
    # db connection
    db_host: str = "localhost"
    db_port: int = 7687  # use 7688 for test db
    # db settings
    text_index_name: str = "modelDocuments"
