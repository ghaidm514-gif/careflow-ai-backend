"""SQLAlchemy adapter for ITriageAnswerRepository (append-only).

FROZEN MVP SEMANTICS: one answer per (request_id, question_id). A concurrent
duplicate that slips past the caller's pre-check hits the database unique
constraint uq_triage_answers_request_question and ONLY that violation is
translated into the frozen QuestionAlreadyAnsweredException. Any other
IntegrityError (foreign key, nullability, other constraints) propagates
unchanged.

TRANSACTION OWNERSHIP: the repository translates the error but does NOT repair
the transaction — after the failed flush the session is in a failed state and
the CALLER owns the rollback. The repository never calls commit, rollback,
close, or begin.
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

_DUPLICATE_ANSWER_CONSTRAINT = "uq_triage_answers_request_question"
# SQLite reports unique violations by column list, not constraint name.
_SQLITE_DUPLICATE_MARKER = (
    "UNIQUE constraint failed: triage_answers.request_id, triage_answers.question_id"
)


def _is_duplicate_answer_violation(exc: IntegrityError) -> bool:
    """True only for the (request_id, question_id) unique-constraint violation.

    Extraction paths, most specific first:
    - psycopg: exc.orig.diag.constraint_name
    - asyncpg via SQLAlchemy: exc.orig.__cause__.constraint_name
    - message fallback (constraint name appears in PostgreSQL error text)
    - SQLite: fixed column-list marker (no constraint names in messages)
    """
    orig = exc.orig
    diag = getattr(orig, "diag", None)
    if getattr(diag, "constraint_name", None) == _DUPLICATE_ANSWER_CONSTRAINT:
        return True
    cause = getattr(orig, "__cause__", None)
    if getattr(cause, "constraint_name", None) == _DUPLICATE_ANSWER_CONSTRAINT:
        return True
    text = str(orig or exc)
    return _DUPLICATE_ANSWER_CONSTRAINT in text or _SQLITE_DUPLICATE_MARKER in text


class SQLAlchemyTriageAnswerRepository(ITriageAnswerRepository):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def create(self, answer: TriageAnswer) -> TriageAnswer:
        row = answer_to_row(answer)
        self._session.add(row)
        try:
            await self._session.flush()
        except IntegrityError as exc:
            if _is_duplicate_answer_violation(exc):
                raise QuestionAlreadyAnsweredException(
                    details={
                        "request_id": str(answer.request_id),
                        "question_id": answer.question_id,
                    }
                ) from exc
            raise  # any other integrity violation propagates unchanged
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
