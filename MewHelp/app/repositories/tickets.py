from uuid import uuid4

from sqlalchemy.orm import Session

from app.db import Ticket

_TICKET_TYPES = frozenset({"售后", "投诉", "咨询"})


class TicketRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, conversation_id: int, description: str, ticket_type: str) -> Ticket:
        if ticket_type not in _TICKET_TYPES:
            raise ValueError("ticket_type must be 售后, 投诉, or 咨询")

        ticket = Ticket(
            ticket_no=f"TKT-{uuid4().hex[:28]}",
            conversation_id=conversation_id,
            description=description,
            ticket_type=ticket_type,
            status="待处理",
        )
        self._session.add(ticket)
        self._session.commit()
        return ticket
