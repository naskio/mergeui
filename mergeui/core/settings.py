import pydantic as pd
from loguru import logger
from pathlib import Path
import pydantic_settings as pds

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
    # db settings
    text_index_name: str = "modelDocuments"
