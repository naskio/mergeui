from rq.worker_pool import WorkerPool
from core.dependencies import get_settings, get_graph_repository
from loguru import logger
from utils.index.jobs import create_redis_connection
# preloading modules...
# noinspection PyUnresolvedReferences
import utils.index.jobs


def main(*, queues: str = "default", num_workers: int = 1, burst: bool = False):
    settings = get_settings()
    repository: get_graph_repository()
    r = create_redis_connection(settings)
    pool = WorkerPool(queues=[qu.strip() for qu in queues.split()], connection=r, num_workers=num_workers)
    logger.info(f"Starting {num_workers} workers...")
    pool.start(burst=burst, logging_level=settings.rq_logging_level or settings.logging_level)
