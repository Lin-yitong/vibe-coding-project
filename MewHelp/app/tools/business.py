"""LangChain business tools used by the Chapter 2 support assistant."""

import json
from collections.abc import Callable

from langchain_core.tools import BaseTool, tool
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.repositories.faq import FaqRepository
from app.repositories.tickets import TicketRepository
from app.tools.schemas import (
    CreateTicketInput,
    QueryFaqInput,
    QueryLogisticsInput,
    QueryOrderInput,
    QueryProductInput,
)


SessionFactory = Callable[[], Session]


def _json_content(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


@tool(args_schema=QueryOrderInput)
def query_order(order_no: str) -> str:
    """Use when the customer asks for a specific order's status or payment details."""
    return _json_content({"order_no": order_no, "payment_status": "已支付", "status": "已发货"})


@tool(args_schema=QueryProductInput)
def query_product(product_name: str) -> str:
    """Use when the customer asks for the price, stock, or details of one product."""
    return _json_content(
        {"product_name": product_name, "stock": "有货", "title": "MewHelp 演示商品"}
    )


@tool(args_schema=QueryLogisticsInput)
def query_logistics(order_no: str) -> str:
    """Use when the customer asks where a known order is or when it will arrive."""
    return _json_content(
        {"latest_status": "运输中", "order_no": order_no, "provider": "演示快递"}
    )


def build_business_tools(
    *, conversation_id: int, session_factory: SessionFactory = SessionLocal
) -> list[BaseTool]:
    """Build tools bound to one active conversation and short-lived DB sessions."""

    @tool("query_faq", args_schema=QueryFaqInput)
    def query_faq(keyword: str) -> str:
        """Use when the customer asks a policy or common question that may exist in the FAQ."""
        with session_factory() as session:
            matches = FaqRepository(session).search(keyword)
        if not matches:
            return "未找到匹配 FAQ。"
        return _json_content(
            {
                "matches": [
                    {
                        "answer": row.answer,
                        "category": row.category,
                        "question": row.question,
                    }
                    for row in matches
                ]
            }
        )

    @tool("create_ticket", args_schema=CreateTicketInput)
    def create_ticket(description: str, ticket_type: str) -> str:
        """Use when the customer needs human follow-up for after-sales, a complaint, or consultation."""
        with session_factory() as session:
            ticket = TicketRepository(session).create(conversation_id, description, ticket_type)
        return _json_content(
            {
                "status": ticket.status,
                "ticket_no": ticket.ticket_no,
                "ticket_type": ticket.ticket_type,
            }
        )

    return [query_order, query_product, query_logistics, query_faq, create_ticket]
