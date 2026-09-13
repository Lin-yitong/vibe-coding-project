from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.db import Faq


class FaqRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def search(self, keyword: str) -> list[Faq]:
        pattern = f"%{keyword}%"
        statement = (
            select(Faq)
            .where(
                or_(
                    Faq.question.like(pattern),
                    Faq.answer.like(pattern),
                    Faq.category.like(pattern),
                )
            )
            .order_by(Faq.id)
        )
        return list(self._session.scalars(statement))
