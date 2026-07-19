"""ORM non-leakage: every adapter returns exact frozen domain entities.

Runtime checks cover all nine adapters; a static check verifies no public
return annotation references ORM models, Mapped, or the models module.
"""

import inspect
import typing
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import app.infrastructure.repositories as repo_pkg
from app.domain import entities as ent
from app.domain.enums import (
    Language,
    RecommendedService,
    RequestStatus,
    SafetyFlagSeverity,
    StaffDecisionType,
    UrgencyLevel,
)
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
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path}/leak_test.db")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


def _assert_domain(obj, expected_type):
    """Exact domain type, and definitely not an ORM row."""
    assert type(obj) is expected_type, f"expected {expected_type.__name__}, got {type(obj)}"
    assert not isinstance(obj, Base), f"{type(obj).__name__} leaks the declarative base"


def _assert_domain_list(items, expected_type):
    assert isinstance(items, list)
    for item in items:
        _assert_domain(item, expected_type)


async def test_all_nine_adapters_return_domain_entities_only(db_session):
    """Exercise every adapter's single-object and list results."""
    session_repo = SQLAlchemyUserSessionRepository(db_session)
    parent = await session_repo.create(
        ent.UserSession(session_id=uuid4(), language=Language.ENGLISH)
    )
    _assert_domain(parent, ent.UserSession)
    _assert_domain(await session_repo.get_by_id(parent.session_id), ent.UserSession)

    request_repo = SQLAlchemyServiceRequestRepository(db_session)
    request = await request_repo.create(
        ent.ServiceRequest(
            request_id=uuid4(),
            session_id=parent.session_id,
            initial_description="demo",
            language=Language.ENGLISH,
            status=RequestStatus.IN_TRIAGE,
        )
    )
    _assert_domain(request, ent.ServiceRequest)
    _assert_domain(await request_repo.get_by_id(request.request_id), ent.ServiceRequest)
    _assert_domain(await request_repo.update(request), ent.ServiceRequest)
    _assert_domain_list(await request_repo.list_by_session(parent.session_id), ent.ServiceRequest)

    message_repo = SQLAlchemyConversationMessageRepository(db_session)
    _assert_domain(
        await message_repo.create(
            ent.ConversationMessage(
                message_id=uuid4(),
                request_id=request.request_id,
                role="user",
                content="hello",
                message_type="user_response",
            )
        ),
        ent.ConversationMessage,
    )
    _assert_domain_list(
        await message_repo.list_by_request(request.request_id), ent.ConversationMessage
    )

    answer_repo = SQLAlchemyTriageAnswerRepository(db_session)
    _assert_domain(
        await answer_repo.create(
            ent.TriageAnswer(
                answer_id=uuid4(),
                request_id=request.request_id,
                question_id="q1",
                question_text="Q?",
                user_answer="A",
            )
        ),
        ent.TriageAnswer,
    )
    _assert_domain(
        await answer_repo.get_by_request_and_question(request.request_id, "q1"),
        ent.TriageAnswer,
    )
    _assert_domain_list(await answer_repo.list_by_request(request.request_id), ent.TriageAnswer)

    flag_repo = SQLAlchemySafetyFlagRepository(db_session)
    _assert_domain(
        await flag_repo.create(
            ent.SafetyFlag(
                flag_id=uuid4(),
                request_id=request.request_id,
                rule_code="TEST",
                severity=SafetyFlagSeverity.WARNING,
                description="d",
            )
        ),
        ent.SafetyFlag,
    )
    _assert_domain_list(await flag_repo.list_by_request(request.request_id), ent.SafetyFlag)

    rec_repo = SQLAlchemyAIRecommendationRepository(db_session)
    rec = await rec_repo.add(
        ent.AIRecommendation(
            recommendation_id=uuid4(),
            request_id=request.request_id,
            recommended_service=RecommendedService.PRIMARY_CARE,
            urgency_level=UrgencyLevel.MEDIUM,
            rationale="r",
            confidence=0.8,
            confidence_reason="c",
        )
    )
    _assert_domain(rec, ent.AIRecommendation)
    _assert_domain(await rec_repo.get(rec.recommendation_id), ent.AIRecommendation)
    _assert_domain(await rec_repo.get_latest_for_request(request.request_id), ent.AIRecommendation)
    _assert_domain_list(await rec_repo.list_for_request(request.request_id), ent.AIRecommendation)

    staff_repo = SQLAlchemyStaffUserRepository(db_session)
    staff = await staff_repo.create(
        ent.StaffUser(staff_user_id=uuid4(), email="n@test.local", role="triage_nurse")
    )
    _assert_domain(staff, ent.StaffUser)
    _assert_domain(await staff_repo.get_by_id(staff.staff_user_id), ent.StaffUser)
    _assert_domain(await staff_repo.get_by_email("n@test.local"), ent.StaffUser)

    decision_repo = SQLAlchemyStaffDecisionRepository(db_session)
    _assert_domain(
        await decision_repo.create(
            ent.StaffDecision(
                decision_id=uuid4(),
                request_id=request.request_id,
                staff_user_id=staff.staff_user_id,
                decision_type=StaffDecisionType.ACCEPT,
            )
        ),
        ent.StaffDecision,
    )
    _assert_domain_list(await decision_repo.list_by_request(request.request_id), ent.StaffDecision)

    audit_repo = SQLAlchemyAuditLogRepository(db_session)
    _assert_domain(
        await audit_repo.create(
            ent.AuditLog(
                log_id=uuid4(),
                request_id=request.request_id,
                actor="system",
                action="TEST",
            )
        ),
        ent.AuditLog,
    )
    _assert_domain_list(await audit_repo.list_by_request(request.request_id), ent.AuditLog)


def _iter_adapter_public_methods():
    for name in repo_pkg.__all__:
        adapter = getattr(repo_pkg, name)
        for method_name, method in inspect.getmembers(adapter, inspect.isfunction):
            if not method_name.startswith("_"):
                yield adapter, method_name, method


def test_static_return_annotations_reference_no_orm_types():
    """No public adapter return annotation references ORM models, Mapped, or
    the infrastructure models module."""
    violations = []
    for adapter, method_name, method in _iter_adapter_public_methods():
        hints = typing.get_type_hints(method)
        ret = hints.get("return")
        rendered = repr(ret)
        if any(marker in rendered for marker in ("Model", "Mapped", "app.infrastructure.models")):
            violations.append(f"{adapter.__name__}.{method_name} -> {rendered}")
    assert violations == [], f"ORM types leak through annotations: {violations}"
