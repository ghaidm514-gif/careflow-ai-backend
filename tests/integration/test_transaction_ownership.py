"""Transaction-ownership contract: the caller owns commit/rollback.

Repositories flush but never commit; nothing persists unless the caller
commits, and a caller rollback removes everything flushed in the transaction.
The PostgreSQL shared-transaction variant lives in the postgresql-marked suite.
"""

import re
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.exc import PendingRollbackError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.domain.entities import ServiceRequest, TriageAnswer, UserSession
from app.domain.enums import Language, RequestStatus
from app.domain.exceptions import QuestionAlreadyAnsweredException
from app.infrastructure.models import Base, UserSessionModel
from app.infrastructure.repositories import (
    SQLAlchemyServiceRequestRepository,
    SQLAlchemyTriageAnswerRepository,
    SQLAlchemyUserSessionRepository,
)


@pytest.fixture
async def engine(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path}/txn_test.db")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
def session_factory(engine):
    return async_sessionmaker(engine, expire_on_commit=False)


def _session_entity() -> UserSession:
    return UserSession(session_id=uuid4(), language=Language.ENGLISH)


async def test_insert_without_commit_then_rollback_does_not_persist(session_factory):
    """Repository insert + caller rollback → nothing persists."""
    entity = _session_entity()
    async with session_factory() as session:
        await SQLAlchemyUserSessionRepository(session).create(entity)
        await session.rollback()  # caller decision

    async with session_factory() as fresh:
        assert await SQLAlchemyUserSessionRepository(fresh).get_by_id(entity.session_id) is None


async def test_flushed_data_visible_in_same_transaction_before_rollback(session_factory):
    """Flushed rows are queryable inside the same open transaction."""
    entity = _session_entity()
    async with session_factory() as session:
        repo = SQLAlchemyUserSessionRepository(session)
        await repo.create(entity)
        visible = await repo.get_by_id(entity.session_id)  # same transaction
        assert visible is not None
        await session.rollback()

    async with session_factory() as fresh:
        assert await SQLAlchemyUserSessionRepository(fresh).get_by_id(entity.session_id) is None


async def test_separate_session_cannot_see_uncommitted_data(session_factory):
    """A second session never observes another transaction's uncommitted rows."""
    entity = _session_entity()
    async with session_factory() as writer:
        await SQLAlchemyUserSessionRepository(writer).create(entity)
        async with session_factory() as reader:
            result = await reader.execute(
                select(UserSessionModel).where(UserSessionModel.session_id == entity.session_id)
            )
            assert result.scalar_one_or_none() is None
        await writer.rollback()


async def test_integrity_error_session_recovery_flow(session_factory):
    """The exact 8-step recovery contract.

    The repository translates the duplicate-answer violation but does NOT
    repair the transaction; the caller owns rollback.
    """
    async with session_factory() as session:
        # 1. valid parent + valid answer
        parent = await SQLAlchemyUserSessionRepository(session).create(_session_entity())
        request = await SQLAlchemyServiceRequestRepository(session).create(
            ServiceRequest(
                request_id=uuid4(),
                session_id=parent.session_id,
                initial_description="demo",
                language=Language.ENGLISH,
                status=RequestStatus.IN_TRIAGE,
            )
        )
        repo = SQLAlchemyTriageAnswerRepository(session)
        await repo.create(
            TriageAnswer(
                answer_id=uuid4(),
                request_id=request.request_id,
                question_id="q1",
                question_text="Q?",
                user_answer="first",
            )
        )
        await session.commit()

        # 2 + 3. duplicate raises the frozen exception
        with pytest.raises(QuestionAlreadyAnsweredException):
            await repo.create(
                TriageAnswer(
                    answer_id=uuid4(),
                    request_id=request.request_id,
                    question_id="q1",
                    question_text="Q?",
                    user_answer="duplicate",
                )
            )

        # 4 + 5. repository did NOT roll back: the session is left in a failed
        # transaction state, so any further use raises PendingRollbackError.
        with pytest.raises(PendingRollbackError):
            await session.execute(select(UserSessionModel))

        # 6. caller executes rollback
        await session.rollback()

        # 7 + 8. session is usable again; another valid insert succeeds
        recovered = await repo.create(
            TriageAnswer(
                answer_id=uuid4(),
                request_id=request.request_id,
                question_id="q2",
                question_text="Next?",
                user_answer="works",
            )
        )
        await session.commit()
        assert recovered.question_id == "q2"
        answers = await repo.list_by_request(request.request_id)
        assert [a.question_id for a in answers] == ["q1", "q2"]


FORBIDDEN_SESSION_CALLS = re.compile(
    r"\.\s*(commit|rollback|close|begin)\s*\(|create_async_engine|async_sessionmaker"
)


def test_repositories_never_manage_transactions_or_engines():
    """Static scan: no adapter calls commit/rollback/close/begin or constructs
    engines/session factories. Transaction lifecycle belongs to the caller."""
    repo_dir = Path("app/infrastructure/repositories")
    violations = []
    for path in sorted(repo_dir.glob("*.py")):
        for lineno, line in enumerate(path.read_text().splitlines(), 1):
            stripped = line.split("#")[0]
            if FORBIDDEN_SESSION_CALLS.search(stripped):
                violations.append(f"{path.name}:{lineno}: {line.strip()}")
    assert violations == [], f"forbidden transaction/engine management: {violations}"
