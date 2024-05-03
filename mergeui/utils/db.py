from loguru import logger
from core.settings import Settings
import gqlalchemy as gq


def create_db_connection(settings: Settings) -> gq.Memgraph:
    logger.debug(f"Creating database connection for {settings.app_name}...")
    return gq.Memgraph(
        host=settings.db_host,
        port=settings.db_port,
    )
