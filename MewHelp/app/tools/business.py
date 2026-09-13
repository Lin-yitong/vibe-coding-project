"""LangChain business tools used by the Chapter 2 support assistant."""

import json
from typing import Protocol

from langchain_core.tools import BaseTool, tool

from app.repositories.faq import FaqRepository
from app.repositories.tickets import TicketRepository
from app.tools.schemas import (
    CreateTicketInput,
    QueryFaqInput,
    QueryLogisticsInput,
    QueryOrderInput,
    QueryProductInput,
)


class _FaqSearcher(Protocol):
    def search(self, keyword: str) -> list[object]: ...


class _TicketCreator(Protocol):
    def create(self, conversation_id: int, description: str, ticket_type: str) -> object: ...


_faq_repository: _FaqSearcher | None = None
_ticket_repository: _TicketCreator | None = None


def configure_business_repositories(
    *,
    faq_repository: FaqRepository | None = None,
    ticket_repository: TicketRepository | None = None,
) -> None:
    """Provide the repository dependencies for the two persistence-backed tools."""
    global _faq_repository, _ticket_repository
    if faq_repository is not None:
        _faq_repository = faq_repository
    if ticket_repository is not None:
        _ticket_repository = ticket_repository


def _json_content(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


@tool(args_schema=QueryOrderInput)
def query_order(order_no: str) -> str:
    """Use when the customer asks for a specific order's status or payment details."""
    return _json_content({"order_no": order_no, "payment_status": "已支付", "status": "已发货"})


@tool(args_schema=QueryProductInput)
def query_product(product_id: str) -> str:
    """Use when the customer asks for the price, stock, or details of one product."""
    return _json_content({"product_id": product_id, "stock": "有货", "title": "MewHelp 演示商品"})


@tool(args_schema=QueryLogisticsInput)
def query_logistics(order_no: str) -> str:
    """Use when the customer asks where a known order is or when it will arrive."""
    return _json_content(
        {"latest_status": "运输中", "order_no": order_no, "provider": "演示快递"}
    )


@tool(args_schema=QueryFaqInput)
def query_faq(keyword: str) -> str:
    """Use when the customer asks a policy or common question that may exist in the FAQ."""
    if _faq_repository is None:
        raise RuntimeError("FAQ repository is unavailable")

    matches = _faq_repository.search(keyword)
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


@tool(args_schema=CreateTicketInput)
def create_ticket(conversation_id: int, description: str, ticket_type: str) -> str:
    """Use when the customer needs human follow-up for after-sales, a complaint, or consultation."""
    if _ticket_repository is None:
        raise RuntimeError("Ticket repository is unavailable")

    ticket = _ticket_repository.create(conversation_id, description, ticket_type)
    return _json_content(
        {
            "status": ticket.status,
            "ticket_no": ticket.ticket_no,
            "ticket_type": ticket.ticket_type,
        }
    )


REGISTERED_TOOLS: list[BaseTool] = [
    query_order,
    query_product,
    query_logistics,
    query_faq,
    create_ticket,
]
