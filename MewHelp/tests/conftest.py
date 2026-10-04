from collections.abc import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    """Use SQLite tables whose integer keys retain MySQL autoincrement semantics."""
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.connection.driver_connection.executescript(
            """
            CREATE TABLE conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id VARCHAR(64) NOT NULL,
                status VARCHAR(16) NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id INTEGER NOT NULL,
                role VARCHAR(16) NOT NULL,
                content TEXT,
                tool_calls JSON,
                tool_call_id VARCHAR(128),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE faq (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question VARCHAR(255) NOT NULL,
                answer TEXT NOT NULL,
                category VARCHAR(64) NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE tickets (
                ticket_no VARCHAR(32) PRIMARY KEY,
                conversation_id INTEGER NOT NULL,
                description TEXT NOT NULL,
                ticket_type VARCHAR(16) NOT NULL,
                status VARCHAR(16) NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
    session = sessionmaker(bind=engine, expire_on_commit=False)()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()
