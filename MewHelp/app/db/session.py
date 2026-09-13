from collections.abc import Generator

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import Settings


def _database_url() -> str:
    # Supply non-database settings only so Settings can still read DATABASE_URL from .env.
    return Settings(litellm_base_url="", litellm_api_key="").database_url


def create_database_engine(database_url: str | None = None) -> Engine:
    return create_engine(database_url or _database_url(), pool_pre_ping=True)


engine: Engine | None = None
SessionLocal = sessionmaker(autoflush=False, autocommit=False, expire_on_commit=False)


def get_database_engine() -> Engine:
    global engine
    if engine is None:
        engine = create_database_engine()
    return engine


def get_db_session() -> Generator[Session, None, None]:
    session = SessionLocal(bind=get_database_engine())
    try:
        yield session
    finally:
        session.close()
