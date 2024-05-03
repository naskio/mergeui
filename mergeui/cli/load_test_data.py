from loguru import logger
from core.settings import Settings
from core.db import DatabaseConnection


def main():
    settings = Settings()
    db_conn = DatabaseConnection(settings)
    db_conn.setup()
    db_conn.populate_from_json(settings.project_dir / "tests/test_data/graph.json")
    logger.success("Test data loaded")


if __name__ == '__main__':
    main()
