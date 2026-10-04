from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_compose_has_ephemeral_mysql_and_healthcheck() -> None:
    compose = (PROJECT_ROOT / "docker-compose.yml").read_text()

    assert "mysql:8" in compose
    assert "healthcheck:" in compose
    assert "./db/init:/docker-entrypoint-initdb.d:ro" in compose
    # Service-level volumes is required for the read-only init bind mount; a
    # top-level volumes block would declare prohibited persistent storage.
    assert "\nvolumes:\n" not in compose


def test_sql_initialization_contains_required_schema_and_seed_constraints() -> None:
    schema = (PROJECT_ROOT / "db/init/001_schema.sql").read_text()
    seed = (PROJECT_ROOT / "db/init/002_seed.sql").read_text()

    for table in ("conversations", "messages", "faq", "tickets"):
        assert f"CREATE TABLE {table}" in schema
    assert "ENUM('售后', '投诉', '咨询')" in schema
    assert "退货政策是什么" in seed
    assert "邮费" not in seed
