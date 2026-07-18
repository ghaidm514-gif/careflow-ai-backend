"""Repository adapter contract tests.

Each test runs against a fresh async SQLite database with the schema created
from ORM metadata. These verify port-contract behavior (round-trips, ordering,
not-found, constraint translation); PostgreSQL-specific enforcement is covered
by the postgresql-marked suite.
"""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.domain.entities import (
    AIRecommendation,
    AuditLog,
    ConversationMessage,
    SafetyFlag,
    ServiceRequest,
    StaffDecision,
    StaffUser,
    TriageAnswer,
    UserSession,
)
from app.domain.enums import (
    Language,
    RecommendedService,
    RequestStatus,
    SafetyFlagSeverity,
    StaffDecisionType,
    UrgencyLevel,
)
from app.domain.exceptions import QuestionAlreadyAnsweredException, ResourceNotFoundException
from app.infrastructure.models import Base
from app.infrastructure.repositories import (
    SQLAlchemyAIRecommendationRepository,
    SQLAlchemyAuditLogRepository,
    SQLAlchemyConversationMessageRepository,
    SQLAlchemySafetyFlagRepository,
    SQLAlchemyServiceRequestRepository,
    SQLAlchemyStaffDecisionRepository,
    SQLAlchemyStaffUserRepository,
    SQLAlchemyTriageAnswerRepository,
    SQLAlchemyUserSessionRepository,
)


@pytest.fixture
async def db_session(tmp_path):
    """Fresh async SQLite database per test; schema from ORM metadata."""
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path}/repo_test.db")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


def _session_entity() -> UserSession:
    return UserSession(session_id=uuid4(), language=Language.ENGLISH)


def _request_entity(session_id) -> ServiceRequest:
    return ServiceRequest(
        request_id=uuid4(),
        session_id=session_id,
        initial_description="demo request",
        language=Language.ENGLISH,
        status=RequestStatus.PENDING,
    )


async def _seed_request(db_session) -> ServiceRequest:
    session = await SQLAlchemyUserSessionRepository(db_session).create(_session_entity())
    return await SQLAlchemyServiceRequestRepository(db_session).create(
        _request_entity(session.session_id)
    )


async def test_user_session_roundtrip(db_session):
    """create → get_by_id preserves all fields; missing id returns None."""
    repo = SQLAlchemyUserSessionRepository(db_session)
    created = await repo.create(_session_entity())
    fetched = await repo.get_by_id(created.session_id)
    assert fetched == created
    assert await repo.get_by_id(uuid4()) is None


async def test_service_request_update_mutable_fields(db_session):
    """update persists status transitions; entity type is preserved."""
    request = await _seed_request(db_session)
    repo = SQLAlchemyServiceRequestRepository(db_session)
    request.status = RequestStatus.INTAKE_COMPLETE
    updated = await repo.update(request)
    assert updated.status is RequestStatus.INTAKE_COMPLETE
    fetched = await repo.get_by_id(request.request_id)
    assert fetched is not None and fetched.status is RequestStatus.INTAKE_COMPLETE


async def test_service_request_update_missing_raises(db_session):
    """update on a nonexistent request raises the frozen not-found exception."""
    repo = SQLAlchemyServiceRequestRepository(db_session)
    ghost = _request_entity(uuid4())
    with pytest.raises(ResourceNotFoundException):
        await repo.update(ghost)


async def test_service_request_list_by_session_ordered(db_session):
    """list_by_session returns requests in created_at order."""
    session = await SQLAlchemyUserSessionRepository(db_session).create(_session_entity())
    repo = SQLAlchemyServiceRequestRepository(db_session)
    base = datetime.now(timezone.utc)
    ids = []
    for offset in (2, 0, 1):  # insert out of chronological order
        entity = _request_entity(session.session_id)
        entity.created_at = base + timedelta(seconds=offset)
        created = await repo.create(entity)
        ids.append((offset, created.request_id))
    listed = await repo.list_by_session(session.session_id)
    assert [r.request_id for r in listed] == [rid for _, rid in sorted(ids)]


async def test_conversation_messages_ordered(db_session):
    """Messages come back in chronological order regardless of insert order."""
    request = await _seed_request(db_session)
    repo = SQLAlchemyConversationMessageRepository(db_session)
    base = datetime.now(timezone.utc)
    for offset, content in ((1, "second"), (0, "first"), (2, "third")):
        await repo.create(
            ConversationMessage(
                message_id=uuid4(),
                request_id=request.request_id,
                role="user",
                content=content,
                message_type="user_response",
                created_at=base + timedelta(seconds=offset),
            )
        )
    listed = await repo.list_by_request(request.request_id)
    assert [m.content for m in listed] == ["first", "second", "third"]


async def test_triage_answer_roundtrip_and_lookup(db_session):
    """create → get_by_request_and_question; unknown question returns None."""
    request = await _seed_request(db_session)
    repo = SQLAlchemyTriageAnswerRepository(db_session)
    answer = TriageAnswer(
        answer_id=uuid4(),
        request_id=request.request_id,
        question_id="q1",
        question_text="When did it start?",
        user_answer="Yesterday",
    )
    await repo.create(answer)
    found = await repo.get_by_request_and_question(request.request_id, "q1")
    assert found is not None and found.user_answer == "Yesterday"
    assert await repo.get_by_request_and_question(request.request_id, "q9") is None


async def test_duplicate_answer_raises_frozen_exception(db_session):
    """A concurrent duplicate answer surfaces QuestionAlreadyAnsweredException."""
    request = await _seed_request(db_session)
    repo = SQLAlchemyTriageAnswerRepository(db_session)
    await repo.create(
        TriageAnswer(
            answer_id=uuid4(),
            request_id=request.request_id,
            question_id="q1",
            question_text="Q?",
            user_answer="first",
        )
    )
    with pytest.raises(QuestionAlreadyAnsweredException):
        await repo.create(
            TriageAnswer(
                answer_id=uuid4(),
                request_id=request.request_id,
                question_id="q1",
                question_text="Q?",
                user_answer="different",
            )
        )


async def test_safety_flags_roundtrip(db_session):
    """Safety flags persist and list in trigger order."""
    request = await _seed_request(db_session)
    repo = SQLAlchemySafetyFlagRepository(db_session)
    flag = SafetyFlag(
        flag_id=uuid4(),
        request_id=request.request_id,
        rule_code="CHEST_PAIN_DIFFICULTY_BREATHING",
        severity=SafetyFlagSeverity.CRITICAL,
        description="detected",
        action_taken="EMERGENCY_ESCALATION",
    )
    await repo.create(flag)
    listed = await repo.list_by_request(request.request_id)
    assert listed == [flag]


def _recommendation(request_id, seq) -> AIRecommendation:
    return AIRecommendation(
        recommendation_id=uuid4(),
        request_id=request_id,
        recommended_service=RecommendedService.PRIMARY_CARE,
        urgency_level=UrgencyLevel.MEDIUM,
        rationale=f"rev {seq}",
        confidence=0.8,
        confidence_reason="reason",
        sequence_number=seq,
    )


async def test_recommendation_append_only_versions(db_session):
    """Multiple versions per request; list ascending; latest is highest sequence."""
    request = await _seed_request(db_session)
    repo = SQLAlchemyAIRecommendationRepository(db_session)
    # add out of order to prove ordering is by sequence, not insertion
    await repo.add(_recommendation(request.request_id, 2))
    await repo.add(_recommendation(request.request_id, 1))
    await repo.add(_recommendation(request.request_id, 3))

    listed = await repo.list_for_request(request.request_id)
    assert [r.sequence_number for r in listed] == [1, 2, 3]

    latest = await repo.get_latest_for_request(request.request_id)
    assert latest is not None and latest.sequence_number == 3
    assert latest.rationale == "rev 3"


async def test_recommendation_get_and_not_found(db_session):
    """get returns the row by id; unknown id returns None."""
    request = await _seed_request(db_session)
    repo = SQLAlchemyAIRecommendationRepository(db_session)
    created = await repo.add(_recommendation(request.request_id, 1))
    fetched = await repo.get(created.recommendation_id)
    assert fetched == created
    assert await repo.get(uuid4()) is None
    assert await repo.get_latest_for_request(uuid4()) is None


async def test_staff_user_roundtrip_and_email_lookup(db_session):
    """Role converts str ⇄ enum across the boundary; email lookup works."""
    repo = SQLAlchemyStaffUserRepository(db_session)
    user = StaffUser(staff_user_id=uuid4(), email="nurse@test.local", role="triage_nurse")
    created = await repo.create(user)
    assert created.role == "triage_nurse"
    assert await repo.get_by_email("nurse@test.local") == created
    assert await repo.get_by_email("ghost@test.local") is None


async def test_staff_decisions_append_and_order(db_session):
    """Decisions accumulate append-only in decided_at order."""
    request = await _seed_request(db_session)
    staff = await SQLAlchemyStaffUserRepository(db_session).create(
        StaffUser(staff_user_id=uuid4(), email="n@test.local", role="triage_nurse")
    )
    repo = SQLAlchemyStaffDecisionRepository(db_session)
    base = datetime.now(timezone.utc)
    for offset, dtype in ((1, StaffDecisionType.ESCALATE), (0, StaffDecisionType.ACCEPT)):
        await repo.create(
            StaffDecision(
                decision_id=uuid4(),
                request_id=request.request_id,
                staff_user_id=staff.staff_user_id,
                decision_type=dtype,
                reason="review" if dtype is StaffDecisionType.ESCALATE else None,
                decided_at=base + timedelta(seconds=offset),
            )
        )
    listed = await repo.list_by_request(request.request_id)
    assert [d.decision_type for d in listed] == [
        StaffDecisionType.ACCEPT,
        StaffDecisionType.ESCALATE,
    ]


async def test_audit_log_roundtrip_with_details(db_session):
    """Audit entries persist JSON details and versioning fields."""
    request = await _seed_request(db_session)
    repo = SQLAlchemyAuditLogRepository(db_session)
    log = AuditLog(
        log_id=uuid4(),
        request_id=request.request_id,
        actor="ai_system",
        action="INTAKE_CLASSIFIED",
        details={"classification": "healthcare", "confidence": 0.92},
        model_provider="anthropic",
        model_name="claude-3-5-sonnet-20241022",
        prompt_version="1.0.0",
        workflow_version="1.0.0",
    )
    await repo.create(log)
    listed = await repo.list_by_request(request.request_id)
    assert listed == [log]
    assert listed[0].details == {"classification": "healthcare", "confidence": 0.92}


async def test_empty_lists_for_unknown_request(db_session):
    """Every list method returns an empty list for an unknown request."""
    ghost = uuid4()
    assert await SQLAlchemyConversationMessageRepository(db_session).list_by_request(ghost) == []
    assert await SQLAlchemyTriageAnswerRepository(db_session).list_by_request(ghost) == []
    assert await SQLAlchemySafetyFlagRepository(db_session).list_by_request(ghost) == []
    assert await SQLAlchemyAIRecommendationRepository(db_session).list_for_request(ghost) == []
    assert await SQLAlchemyStaffDecisionRepository(db_session).list_by_request(ghost) == []
    assert await SQLAlchemyAuditLogRepository(db_session).list_by_request(ghost) == []
