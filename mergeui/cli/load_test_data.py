from loguru import logger
from core.dependencies import get_db_connection


def main():
    db_conn = get_db_connection()
    db_conn.setup()
    db_conn.populate_from_json_file(db_conn.settings.project_dir / "tests/test_data/graph.json")
    logger.success("Test data loaded")


if __name__ == '__main__':
    main()
