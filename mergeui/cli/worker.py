from loguru import logger
from rq import Worker
from mergeui.core.dependencies import get_settings, get_graph_repository
from mergeui.utils.index.jobs import create_redis_connection
# preloading modules...
# noinspection PyUnresolvedReferences
import mergeui.utils.index.jobs


def main(*, queues: str = "default", burst: bool = False):
    settings = get_settings()
    repository: get_graph_repository()
    r = create_redis_connection(settings)
    w = Worker(queues=[qu.strip() for qu in queues.split()], connection=r)
    logger.info("Starting worker...")
    w.work(burst=burst, logging_level=str(settings.rq_logging_level or settings.logging_level))
