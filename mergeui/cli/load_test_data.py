from loguru import logger
from core.dependencies import get_db_connection


def main():
    db_conn = get_db_connection()
    db_conn.reset()
    db_conn.setup_pre_populate()
    db_conn.populate_from_json_file(db_conn.settings.project_dir / "tests/test_data/graph.json")
    db_conn.setup_post_populate()
    logger.success("Test data loaded")


if __name__ == '__main__':
    main()
