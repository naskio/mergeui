from loguru import logger
from core.dependencies import get_db_connection


def main():
    db_conn = get_db_connection()
    db_conn.reset()
    logger.success("Database reset successfully")


if __name__ == '__main__':
    main()
