"""Creates the schema and loads the demo fast-food catalog.

Usage:  python -m scripts.init_db
"""

import logging

import app.domain.models  # noqa: F401  (registers the tables on Base.metadata)
from app.core.config import get_settings
from app.core.database import Base, get_engine, get_session_factory
from app.core.logging import configure_logging
from app.repositories.seed import seed_catalog
from app.repositories.unit_of_work import SqlAlchemyUnitOfWork

logger = logging.getLogger("init_db")


def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)

    engine = get_engine()
    # create_all only adds missing tables; schema changes on existing tables
    # will need Alembic migrations once the model stabilises.
    Base.metadata.create_all(engine)
    logger.info("Schema ready on %s", engine.url.render_as_string(hide_password=True))

    ingredients, products = seed_catalog(SqlAlchemyUnitOfWork(get_session_factory()))
    logger.info("Created %d ingredients and %d products", ingredients, products)


if __name__ == "__main__":
    main()
