from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings


class Base(DeclarativeBase):
    pass


def build_engine(database_url: str, echo: bool = False) -> Engine:
    connect_args: dict = {}
    if database_url.startswith("sqlite"):
        # FastAPI serves requests from a thread pool; SQLite's default
        # same-thread guard would reject connections reused across threads.
        connect_args["check_same_thread"] = False
    elif database_url.startswith("postgresql"):
        # Fail fast: a down database should turn /health/ready into a quick 503,
        # not a request that hangs until the OS gives up on the TCP handshake.
        connect_args["connect_timeout"] = 3
    return create_engine(database_url, echo=echo, pool_pre_ping=True, connect_args=connect_args)


def build_session_factory(engine: Engine) -> sessionmaker[Session]:
    # expire_on_commit=False keeps entities readable after commit, so services
    # can map them to DTOs without triggering lazy reloads on a closed session.
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


@lru_cache
def get_engine() -> Engine:
    return build_engine(get_settings().database_url)


@lru_cache
def get_session_factory() -> sessionmaker[Session]:
    return build_session_factory(get_engine())


def get_session() -> Iterator[Session]:
    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()
