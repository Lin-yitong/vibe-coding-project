from app.config import Settings
from app.db import Conversation, Faq, Message, Ticket


def test_database_url_uses_the_local_mysql_demo_by_default() -> None:
    settings = Settings(
        litellm_base_url="http://localhost:4000/v1",
        litellm_api_key="local",
        _env_file=None,
    )

    assert settings.database_url == (
        "mysql+pymysql://mewhelp:mewhelp@127.0.0.1:3306/mewhelp?charset=utf8mb4"
    )


def test_models_match_the_chapter_two_business_constraints() -> None:
    assert Conversation.__table__.c.status.type.enums == ("进行中", "已转人工", "已结束")
    assert Message.__table__.c.role.type.enums == ("user", "assistant", "tool")
    assert Faq.__table__.c.category.index is True
    assert Ticket.__table__.primary_key.columns.keys() == ["ticket_no"]
    assert Ticket.__table__.c.ticket_type.type.enums == ("售后", "投诉", "咨询")
    assert Ticket.__table__.c.status.type.enums == ("待处理", "已处理")
