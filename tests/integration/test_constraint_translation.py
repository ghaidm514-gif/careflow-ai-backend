"""Constraint-specific IntegrityError translation.

ONLY uq_triage_answers_request_question may become
QuestionAlreadyAnsweredException; every other integrity violation propagates
as IntegrityError unchanged.
"""

from uuid import uuid4

import pytest
from sqlalchemy import event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.domain.entities import ServiceRequest, TriageAnswer, UserSession
from app.domain.enums import Language, RequestStatus
from app.domain.exceptions import QuestionAlreadyAnsweredException
from app.infrastructure.models import Base
from app.infrastructure.repositories import (
    SQLAlchemyServiceRequestRepository,
    SQLAlchemyTriageAnswerRepository,
    SQLAlchemyUserSessionRepository,
)


@pytest.fixture
async def db_session(tmp_path):
    """SQLite session with foreign-key enforcement enabled (off by default)."""
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path}/ct_test.db")

    @event.listens_for(engine.sync_engine, "connect")
    def _fk_on(dbapi_conn, _record):  # pyright: ignore[reportUnusedFunction]
        dbapi_conn.execute("PRAGMA foreign_keys=ON")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


async def _seed_request(db_session) -> ServiceRequest:
    parent = await SQLAlchemyUserSessionRepository(db_session).create(
        UserSession(session_id=uuid4(), language=Language.ENGLISH)
    )
    return await SQLAlchemyServiceRequestRepository(db_session).create(
        ServiceRequest(
            request_id=uuid4(),
            session_id=parent.session_id,
            initial_description="demo",
            language=Language.ENGLISH,
            status=RequestStatus.IN_TRIAGE,
        )
    )


def _answer(request_id, question_id="q1", answer_id=None, user_answer="A") -> TriageAnswer:
    return TriageAnswer(
        answer_id=answer_id or uuid4(),
        request_id=request_id,
        question_id=question_id,
        question_text="Q?",
        user_answer=user_answer,
    )


async def test_duplicate_answer_is_translated(db_session):
    """The (request_id, question_id) violation → frozen domain exception."""
    request = await _seed_request(db_session)
    repo = SQLAlchemyTriageAnswerRepository(db_session)
    await repo.create(_answer(request.request_id))
    with pytest.raises(QuestionAlreadyAnsweredException):
        await repo.create(_answer(request.request_id))


async def test_foreign_key_violation_is_not_translated(db_session):
    """Answer for a nonexistent request → IntegrityError, NOT the domain
    exception."""
    repo = SQLAlchemyTriageAnswerRepository(db_session)
    with pytest.raises(IntegrityError) as exc_info:
        await repo.create(_answer(uuid4()))  # request does not exist
    assert not isinstance(exc_info.value, QuestionAlreadyAnsweredException)


async def test_nullability_violation_is_not_translated(db_session):
    """NOT NULL violation on user_answer → IntegrityError unchanged."""
    request = await _seed_request(db_session)
    repo = SQLAlchemyTriageAnswerRepository(db_session)
    with pytest.raises(IntegrityError) as exc_info:
        # user_answer=None is intentionally illegal: it must hit the DB NOT NULL
        # constraint, not the type checker
        await repo.create(
            _answer(request.request_id, user_answer=None)  # pyright: ignore[reportArgumentType]
        )
    assert not isinstance(exc_info.value, QuestionAlreadyAnsweredException)


async def test_unrelated_unique_violation_propagates_unchanged(db_session):
    """A different unique violation (duplicate primary key) is NOT translated."""
    request = await _seed_request(db_session)
    repo = SQLAlchemyTriageAnswerRepository(db_session)
    first = _answer(request.request_id, question_id="q1")
    await repo.create(first)
    await db_session.commit()
    # same answer_id (PK) but different question — hits pk_ constraint, not
    # the request/question unique constraint
    clone = _answer(request.request_id, question_id="q2", answer_id=first.answer_id)
    with pytest.raises(IntegrityError) as exc_info:
        await repo.create(clone)
    assert not isinstance(exc_info.value, QuestionAlreadyAnsweredException)
