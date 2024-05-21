from rq import Worker
from core.dependencies import get_settings, get_graph_repository
from loguru import logger
from utils.index.jobs import create_redis_connection
# preloading modules...
# noinspection PyUnresolvedReferences
import huggingface_hub as hf
# noinspection PyUnresolvedReferences
from huggingface_hub import hf_api
# noinspection PyUnresolvedReferences
import utils.index.jobs


def main(queues: str = "default"):
    settings = get_settings()
    repository: get_graph_repository()
    r = create_redis_connection(settings)
    w = Worker(queues=[qu.strip() for qu in queues.split()], connection=r)
    logger.info("Starting worker...")
    w.work(logging_level=settings.rq_logging_level or settings.logging_level)
