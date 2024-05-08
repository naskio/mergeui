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
    email: t.Optional[pd.EmailStr] = None
    favicon_path: Path = PROJECT_DIR / 'static/brand/favicon.ico'
    # gradio
    disable_gradio_app: bool = False
    load_custom_js: bool = True
    load_custom_css: bool = True
    # limit results
    max_graph_depth: t.Optional[int] = None
    results_limit: t.Optional[int] = None
    # db connection
    mg_host: str = "localhost"
    mg_port: int = 7687  # use 7688 for test db
    mg_username: str = ""
    mg_password: str = ""
    mg_encrypted: bool = False
    mg_client_name: str = "MergeUI"
    mg_lazy: bool = False
    # db settings
    text_index_name: str = "modelDocuments"


settings = Settings()
