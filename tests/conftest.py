from collections.abc import Iterator

import pytest
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.domain.models  # noqa: F401  (registers tables)
from app.core.database import Base, build_session_factory
from app.repositories.seed import seed_catalog
from app.repositories.unit_of_work import SqlAlchemyUnitOfWork


@pytest.fixture
def engine() -> Iterator[Engine]:
    # StaticPool keeps a single in-memory SQLite connection alive for the whole test;
    # otherwise each new connection would see an empty database.
    engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def session_factory(engine: Engine) -> sessionmaker[Session]:
    return build_session_factory(engine)


@pytest.fixture
def uow(session_factory: sessionmaker[Session]) -> SqlAlchemyUnitOfWork:
    return SqlAlchemyUnitOfWork(session_factory)


@pytest.fixture
def seeded_uow(uow: SqlAlchemyUnitOfWork) -> SqlAlchemyUnitOfWork:
    seed_catalog(uow)
    return uow


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"
