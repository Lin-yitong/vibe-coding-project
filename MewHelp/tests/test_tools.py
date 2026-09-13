import asyncio
import json

import pytest
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import Conversation, Faq, Ticket
from app.tools.business import (
    build_business_tools,
    query_logistics,
    query_order,
    query_product,
)
from app.tools.registry import ToolRegistry
from app.tools.schemas import CreateTicketInput, QueryOrderInput, QueryProductInput


def test_registered_business_tools_have_the_required_names() -> None:
    tools = build_business_tools(conversation_id=1)

    assert [
        tool.name
        for tool in tools
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
        CreateTicketInput(description="需要帮助", ticket_type="退款")


def test_model_facing_tool_schemas_are_exact() -> None:
    tools = {tool.name: tool for tool in build_business_tools(conversation_id=1)}

    assert set(QueryProductInput.model_json_schema()["properties"]) == {"product_name"}
    assert set(tools["query_product"].args_schema.model_json_schema()["properties"]) == {
        "product_name"
    }
    assert set(CreateTicketInput.model_json_schema()["properties"]) == {
        "description",
        "ticket_type",
    }
    assert set(tools["create_ticket"].args_schema.model_json_schema()["properties"]) == {
        "description",
        "ticket_type",
    }
    assert QueryProductInput.model_json_schema()["additionalProperties"] is False
    assert CreateTicketInput.model_json_schema()["additionalProperties"] is False


def test_mock_tools_return_deterministic_json_for_normalized_input() -> None:
    assert query_logistics.invoke({"order_no": " 1001 "}) == query_logistics.invoke(
        {"order_no": "1001"}
    )
    assert query_product.invoke(
        {"product_name": " 演示耳机 "}
    ) == query_product.invoke({"product_name": "演示耳机"})
    for tool, args in (
        (query_order, {"order_no": "1001"}),
        (query_product, {"product_name": "演示耳机"}),
        (query_logistics, {"order_no": "1001"}),
    ):
        assert json.loads(tool.invoke(args))


def test_query_faq_returns_matches_or_clear_no_match_message(db_session: Session) -> None:
    db_session.add(Faq(question="退货政策", answer="七天内可退", category="售后"))
    db_session.commit()
    tools = {
        tool.name: tool
        for tool in build_business_tools(
            conversation_id=1, session_factory=lambda: db_session
        )
    }

    assert "退货政策" in tools["query_faq"].invoke({"keyword": "退货"})
    assert tools["query_faq"].invoke({"keyword": "邮费"}) == "未找到匹配 FAQ。"


def test_create_ticket_uses_ticket_repository(db_session: Session) -> None:
    conversation = Conversation(user_id="demo-user", status="进行中")
    db_session.add(conversation)
    db_session.commit()
    tools = {
        tool.name: tool
        for tool in build_business_tools(
            conversation_id=conversation.id, session_factory=lambda: db_session
        )
    }

    content = json.loads(
        tools["create_ticket"].invoke(
            {
                "description": "商品破损",
                "ticket_type": "售后",
            }
        )
    )

    assert content["ticket_type"] == "售后"
    assert content["status"] == "待处理"
    ticket = db_session.scalar(select(Ticket))
    assert ticket is not None
    assert ticket.conversation_id == conversation.id


def test_create_ticket_rejects_model_supplied_conversation_and_uses_active_one(
    db_session: Session,
) -> None:
    active = Conversation(user_id="demo-user", status="进行中")
    other = Conversation(user_id="demo-user", status="进行中")
    db_session.add_all([active, other])
    db_session.commit()
    tools = build_business_tools(
        conversation_id=active.id, session_factory=lambda: db_session
    )
    registry = ToolRegistry(tools)

    rejected = asyncio.run(
        registry.execute(
            {
                "id": "call-malicious",
                "name": "create_ticket",
                "args": {
                    "conversation_id": other.id,
                    "description": "错误会话",
                    "ticket_type": "投诉",
                },
            }
        )
    )
    create_ticket = next(tool for tool in tools if tool.name == "create_ticket")
    accepted = json.loads(
        create_ticket.invoke({"description": "当前会话", "ticket_type": "咨询"})
    )

    assert rejected.ok is False
    assert rejected.content == "工具参数无效。"
    assert accepted["status"] == "待处理"
    tickets = db_session.scalars(select(Ticket).order_by(Ticket.created_at)).all()
    assert [(ticket.conversation_id, ticket.description) for ticket in tickets] == [
        (active.id, "当前会话")
    ]
