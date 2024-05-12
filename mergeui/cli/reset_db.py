from loguru import logger
from core.dependencies import get_db_connection


def main(setup: bool = True):
    db_conn = get_db_connection()
    getattr(db_conn, "setup" if setup else "reset")()
    logger.success("Database reset successfully")


if __name__ == '__main__':
    main()
