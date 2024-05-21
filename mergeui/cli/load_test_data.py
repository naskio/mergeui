from loguru import logger
from core.dependencies import get_settings, get_db_connection


def main():
    settings = get_settings()
    db_conn = get_db_connection()
    db_conn.reset()
    db_conn.setup_pre_populate()
    db_conn.populate_from_json_file(settings.project_dir / "tests/test_data/graph.json")
    db_conn.setup_post_populate()
    logger.success("Test data loaded")


if __name__ == '__main__':
    main()
