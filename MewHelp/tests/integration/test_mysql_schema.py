"""Integration checks for the schema initialized by the project MySQL container."""

import os

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine


pytestmark = pytest.mark.skipif(
    os.getenv("MEWHELP_RUN_MYSQL_INTEGRATION") != "1",
    reason="run explicitly with `make test-mysql-integration`",
)


@pytest.fixture(scope="module")
def mysql_engine() -> Engine:
    database_url = os.getenv(
        "MEWHELP_MYSQL_INTEGRATION_URL",
        "mysql+pymysql://mewhelp:mewhelp@127.0.0.1:3306/mewhelp?charset=utf8mb4",
    )
    engine = create_engine(database_url, pool_pre_ping=True)
    try:
        with engine.connect() as connection:
            connection.exec_driver_sql("SELECT 1")
        yield engine
    finally:
        engine.dispose()


def test_initialized_mysql_schema_has_required_engines_enums_and_foreign_keys(
    mysql_engine: Engine,
) -> None:
    with mysql_engine.connect() as connection:
        engines = dict(
            connection.execute(
                text(
                    """
                    SELECT TABLE_NAME, ENGINE
                    FROM information_schema.TABLES
                    WHERE TABLE_SCHEMA = DATABASE()
                      AND TABLE_NAME IN ('conversations', 'messages', 'faq', 'tickets')
                    """
                )
            ).all()
        )
        column_types = {
            (table_name, column_name): column_type
            for table_name, column_name, column_type in connection.execute(
                text(
                    """
                    SELECT TABLE_NAME, COLUMN_NAME, COLUMN_TYPE
                    FROM information_schema.COLUMNS
                    WHERE TABLE_SCHEMA = DATABASE()
                      AND (TABLE_NAME, COLUMN_NAME) IN (
                        ('conversations', 'status'),
                        ('messages', 'role'),
                        ('tickets', 'ticket_type'),
                        ('tickets', 'status')
                      )
                    """
                )
            ).all()
        }
        foreign_keys = {
            (table_name, column_name, referenced_table_name, referenced_column_name)
            for table_name, column_name, referenced_table_name, referenced_column_name
            in connection.execute(
                text(
                    """
                    SELECT TABLE_NAME, COLUMN_NAME,
                           REFERENCED_TABLE_NAME, REFERENCED_COLUMN_NAME
                    FROM information_schema.KEY_COLUMN_USAGE
                    WHERE TABLE_SCHEMA = DATABASE()
                      AND REFERENCED_TABLE_NAME IS NOT NULL
                    """
                )
            ).all()
        }

    assert engines == {
        "conversations": "InnoDB",
        "messages": "InnoDB",
        "faq": "InnoDB",
        "tickets": "InnoDB",
    }
    assert column_types == {
        ("conversations", "status"): "enum('进行中','已转人工','已结束')",
        ("messages", "role"): "enum('user','assistant','tool')",
        ("tickets", "ticket_type"): "enum('售后','投诉','咨询')",
        ("tickets", "status"): "enum('待处理','已处理')",
    }
    assert {
        ("messages", "conversation_id", "conversations", "id"),
        ("tickets", "conversation_id", "conversations", "id"),
    }.issubset(foreign_keys)


def test_initialized_mysql_seed_has_return_policy_and_expected_postage_miss(
    mysql_engine: Engine,
) -> None:
    with mysql_engine.connect() as connection:
        return_policy = connection.execute(
            text("SELECT answer FROM faq WHERE question = :question"),
            {"question": "退货政策是什么"},
        ).scalar_one()
        postage_matches = connection.execute(
            text(
                """
                SELECT COUNT(*) FROM faq
                WHERE question LIKE :keyword
                   OR answer LIKE :keyword
                   OR category LIKE :keyword
                """
            ),
            {"keyword": "%邮费%"},
        ).scalar_one()

    assert "7 天内" in return_policy
    assert postage_matches == 0
