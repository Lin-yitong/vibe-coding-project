import json

import pytest
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.db import Conversation, Faq
from app.tools.business import (
    build_business_tools,
    create_ticket,
    query_faq,
    query_logistics,
    query_order,
    query_product,
)
from app.tools.schemas import CreateTicketInput, QueryOrderInput


def test_registered_business_tools_have_the_required_names() -> None:
    assert [
        tool.name
        for tool in (query_order, query_product, query_logistics, query_faq, create_ticket)
    ] == [
        "query_order",
        "query_product",
        "query_logistics",
        "query_faq",
        "create_ticket",
    ]


def test_tool_schemas_reject_blank_order_and_unknown_ticket_type() -> None:
    with pytest.raises(ValidationError):
        QueryOrderInput(order_no=" ")
    with pytest.raises(ValidationError):
        CreateTicketInput(conversation_id=1, description="需要帮助", ticket_type="退款")


def test_mock_tools_return_deterministic_json_for_normalized_input() -> None:
    assert query_logistics.invoke({"order_no": " 1001 "}) == query_logistics.invoke(
        {"order_no": "1001"}
    )
    for tool, args in (
        (query_order, {"order_no": "1001"}),
        (query_product, {"product_id": "sku-1"}),
        (query_logistics, {"order_no": "1001"}),
    ):
        assert json.loads(tool.invoke(args))


def test_query_faq_returns_matches_or_clear_no_match_message(db_session: Session) -> None:
    db_session.add(Faq(question="退货政策", answer="七天内可退", category="售后"))
    db_session.commit()
    tools = {tool.name: tool for tool in build_business_tools(lambda: db_session)}

    assert "退货政策" in tools["query_faq"].invoke({"keyword": "退货"})
    assert tools["query_faq"].invoke({"keyword": "邮费"}) == "未找到匹配 FAQ。"


def test_create_ticket_uses_ticket_repository(db_session: Session) -> None:
    conversation = Conversation(user_id="demo-user", status="进行中")
    db_session.add(conversation)
    db_session.commit()
    tools = {tool.name: tool for tool in build_business_tools(lambda: db_session)}

    content = json.loads(
        tools["create_ticket"].invoke(
            {
                "conversation_id": conversation.id,
                "description": "商品破损",
                "ticket_type": "售后",
            }
        )
    )

    assert content["ticket_type"] == "售后"
    assert content["status"] == "待处理"
