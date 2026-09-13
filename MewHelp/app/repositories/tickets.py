from uuid import uuid4

from sqlalchemy.orm import Session

from app.db import Ticket


class TicketRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, conversation_id: int, description: str, ticket_type: str) -> Ticket:
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
