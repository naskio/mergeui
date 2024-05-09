from loguru import logger
import sys


def set_logger_level(level: str):
    """Set logger level."""
    logger.remove()
    logger.add(sys.stderr, level=level.upper())
