from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import Message
from app.services.conversation_service import ConversationService
def test_conversation_service_reuses_same_conversation_for_session(db_session: Session) -> None:
    service = ConversationService(db_session)

    first = service.get_or_create("browser-1")
    second = service.get_or_create("browser-1")

    assert first.id == second.id
    assert first.user_id == "demo-user"
    assert first.status == "进行中"


def test_message_trace_is_user_request_tool_final_answer(db_session: Session) -> None:
    service = ConversationService(db_session)
    conversation = service.get_or_create("browser-1")
    tool_calls = [{"id": "call-1", "name": "query_faq", "args": {"keyword": "退货"}}]

    service.record_user(conversation, "我要退货")
    service.record_tool_request(conversation, tool_calls)
    service.record_tool_result(conversation, "call-1", '{"matches": 1}')
    service.record_final_answer(conversation, "您可以在签收后七天内申请退货。")

    rows = db_session.scalars(
        select(Message).where(Message.conversation_id == conversation.id).order_by(Message.id)
    ).all()
    assert [message.role for message in rows] == ["user", "assistant", "tool", "assistant"]
    assert rows[0].content == "我要退货"
    assert rows[1].tool_calls == tool_calls
    assert rows[2].tool_call_id == "call-1"
    assert rows[3].content == "您可以在签收后七天内申请退货。"
    assert service.completed_turns_for(conversation) == [
        ("我要退货", "您可以在签收后七天内申请退货。")
    ]
