"""SQLAlchemy adapter for ITriageAnswerRepository (append-only).

FROZEN MVP SEMANTICS: one answer per (request_id, question_id). A concurrent
duplicate that slips past the caller's pre-check hits the database unique
constraint and is translated into the frozen QuestionAlreadyAnsweredException.
"""

from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.ports import ITriageAnswerRepository
from app.domain.entities import TriageAnswer
from app.domain.exceptions import QuestionAlreadyAnsweredException
from app.infrastructure.models import TriageAnswerModel
from app.infrastructure.repositories.mapping import answer_to_entity, answer_to_row


class SQLAlchemyTriageAnswerRepository(ITriageAnswerRepository):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def create(self, answer: TriageAnswer) -> TriageAnswer:
        row = answer_to_row(answer)
        self._session.add(row)
        try:
            await self._session.flush()
        except IntegrityError as exc:
            raise QuestionAlreadyAnsweredException(
                details={
                    "request_id": str(answer.request_id),
                    "question_id": answer.question_id,
                }
            ) from exc
        return answer_to_entity(row)

    async def list_by_request(self, request_id: UUID) -> list[TriageAnswer]:
        result = await self._session.execute(
            select(TriageAnswerModel)
            .where(TriageAnswerModel.request_id == request_id)
            .order_by(TriageAnswerModel.processed_at, TriageAnswerModel.answer_id)
        )
        return [answer_to_entity(row) for row in result.scalars()]

    async def get_by_request_and_question(
        self, request_id: UUID, question_id: str
    ) -> Optional[TriageAnswer]:
        result = await self._session.execute(
            select(TriageAnswerModel).where(
                TriageAnswerModel.request_id == request_id,
                TriageAnswerModel.question_id == question_id,
            )
        )
        row = result.scalar_one_or_none()
        return answer_to_entity(row) if row else None
