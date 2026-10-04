import pytest
from sqlalchemy.orm import Session

from app.db import Conversation, Faq
from app.repositories.faq import FaqRepository
from app.repositories.tickets import TicketRepository


def test_ticket_repository_rejects_unknown_ticket_type(db_session: Session) -> None:
    with pytest.raises(ValueError, match="ticket_type"):
        TicketRepository(db_session).create(
            conversation_id=1,
            description="需要人工协助",
            ticket_type="退款",
        )


def test_faq_search_matches_question_answer_or_category(db_session: Session) -> None:
    db_session.add_all(
        [
            Faq(question="退货政策", answer="七天内可退", category="售后"),
            Faq(question="订单状态", answer="退货款会原路返回", category="支付"),
            Faq(question="联系客服", answer="工作日处理", category="退货流程"),
        ]
    )
    db_session.commit()

    rows = FaqRepository(db_session).search("退货")

    assert [row.question for row in rows] == ["退货政策", "订单状态", "联系客服"]


def test_faq_search_returns_no_match_for_postage(db_session: Session) -> None:
    db_session.add(Faq(question="退货政策", answer="七天内可退", category="售后"))
    db_session.commit()

    assert FaqRepository(db_session).search("邮费") == []


def test_ticket_repository_creates_pending_ticket_with_bounded_number(db_session: Session) -> None:
    conversation = Conversation(user_id="demo-user", status="进行中")
    db_session.add(conversation)
    db_session.commit()

    ticket = TicketRepository(db_session).create(
        conversation_id=conversation.id,
        description="商品破损，需要售后协助",
        ticket_type="售后",
    )

    assert ticket.ticket_no.startswith("TKT-")
    assert len(ticket.ticket_no) <= 32
    assert ticket.status == "待处理"
    assert ticket.conversation_id == conversation.id
