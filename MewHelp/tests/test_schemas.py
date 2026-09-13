import pytest
from pydantic import ValidationError

from app.schemas.chat import ChatRequest
from app.schemas.extract import AfterSalesTicket, ExtractRequest


def test_ticket_rejects_unknown_request_type() -> None:
    with pytest.raises(ValidationError):
        AfterSalesTicket(order_id=None, request_type="cancel", expected_solution=None)


@pytest.mark.parametrize(
    ("field", "value"),
    [("session_id", ""), ("message", "")],
)
def test_chat_request_rejects_empty_required_fields(field: str, value: str) -> None:
    values = {"session_id": "session-1", "message": "Need a refund"}
    values[field] = value

    with pytest.raises(ValidationError):
        ChatRequest(**values)


def test_extract_request_rejects_empty_text() -> None:
    with pytest.raises(ValidationError):
        ExtractRequest(text="")
