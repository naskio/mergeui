import redis
from rq import Worker
from core.dependencies import get_settings, get_graph_repository
from loguru import logger
# preload modules
import huggingface_hub as hf
from huggingface_hub import hf_api
import utils.index.jobs


def main(queues: str = "default"):
    settings = get_settings()
    repository: get_graph_repository()
    r = redis.Redis(
        host=settings.redis_dsn.host,
        port=settings.redis_dsn.port,
        db=settings.redis_dsn.path.replace("/", "")
    )
    w = Worker(queues=[qu.strip() for qu in queues.split()], connection=r)
    logger.info("Starting worker...")
    w.work(logging_level=settings.rq_logging_level or settings.logging_level)
