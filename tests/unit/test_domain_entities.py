"""Tests for domain entities — immutability, mutability, timestamps."""

import dataclasses
from datetime import datetime, timezone
from uuid import uuid4

import pytest

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
    RequestClassification,
    RequestStatus,
    SafetyFlagSeverity,
    StaffDecisionType,
    UrgencyLevel,
)


def test_user_session_is_frozen():
    """UserSession cannot be mutated after creation."""
    session = UserSession(session_id=uuid4(), language=Language.ENGLISH)
    with pytest.raises(dataclasses.FrozenInstanceError):
        session.language = Language.ARABIC  # pyright: ignore[reportAttributeAccessIssue]


def test_service_request_is_mutable():
    """ServiceRequest status and classification change during workflow."""
    request = ServiceRequest(
        request_id=uuid4(),
        session_id=uuid4(),
        initial_description="I have symptoms",
        language=Language.ENGLISH,
        status=RequestStatus.PENDING,
    )
    request.status = RequestStatus.INTAKE_COMPLETE
    request.classification = RequestClassification.HEALTHCARE
    assert request.status is RequestStatus.INTAKE_COMPLETE
    assert request.classification is RequestClassification.HEALTHCARE


def test_conversation_message_is_frozen():
    """ConversationMessage is append-only (immutable)."""
    message = ConversationMessage(
        message_id=uuid4(),
        request_id=uuid4(),
        role="user",
        content="I have pain",
        message_type="user_response",
    )
    with pytest.raises(dataclasses.FrozenInstanceError):
        message.content = "Different content"  # pyright: ignore[reportAttributeAccessIssue]


def test_triage_answer_is_frozen():
    """TriageAnswer is append-only (immutable)."""
    answer = TriageAnswer(
        answer_id=uuid4(),
        request_id=uuid4(),
        question_id="q1",
        question_text="When did symptoms start?",
        user_answer="Three days ago",
    )
    with pytest.raises(dataclasses.FrozenInstanceError):
        answer.user_answer = "Two days ago"  # pyright: ignore[reportAttributeAccessIssue]


def test_safety_flag_is_frozen():
    """SafetyFlag is append-only (immutable)."""
    flag = SafetyFlag(
        flag_id=uuid4(),
        request_id=uuid4(),
        rule_code="CHEST_PAIN_DIFFICULTY_BREATHING",
        severity=SafetyFlagSeverity.CRITICAL,
        description="Chest pain with difficulty breathing detected",
    )
    with pytest.raises(dataclasses.FrozenInstanceError):
        flag.severity = SafetyFlagSeverity.WARNING  # pyright: ignore[reportAttributeAccessIssue]


def test_staff_decision_is_frozen():
    """StaffDecision is append-only (immutable audit record)."""
    decision = StaffDecision(
        decision_id=uuid4(),
        request_id=uuid4(),
        staff_user_id=uuid4(),
        decision_type=StaffDecisionType.ACCEPT,
    )
    with pytest.raises(dataclasses.FrozenInstanceError):
        decision.decision_type = StaffDecisionType.MODIFY  # pyright: ignore[reportAttributeAccessIssue]


def test_audit_log_is_frozen():
    """AuditLog is append-only (immutable)."""
    log = AuditLog(
        log_id=uuid4(),
        request_id=uuid4(),
        actor="ai_system",
        action="INTAKE_CLASSIFIED",
        details={"classification": "healthcare"},
    )
    with pytest.raises(dataclasses.FrozenInstanceError):
        log.action = "DIFFERENT_ACTION"  # pyright: ignore[reportAttributeAccessIssue]


def test_staff_user_is_frozen():
    """StaffUser cannot be mutated after creation."""
    user = StaffUser(staff_user_id=uuid4(), email="nurse@example.com", role="triage_nurse")
    with pytest.raises(dataclasses.FrozenInstanceError):
        user.email = "other@example.com"  # pyright: ignore[reportAttributeAccessIssue]


def test_ai_recommendation_versioning_fields():
    """AIRecommendation carries full versioning metadata."""
    rec = AIRecommendation(
        recommendation_id=uuid4(),
        request_id=uuid4(),
        recommended_service=RecommendedService.PRIMARY_CARE,
        urgency_level=UrgencyLevel.MEDIUM,
        rationale="Symptoms warrant primary care evaluation",
        confidence=0.82,
        confidence_reason="Symptoms match primary care profile",
    )
    assert rec.model_provider == "anthropic"
    assert rec.prompt_version == "1.0.0"
    assert rec.workflow_version == "1.0.0"
    assert rec.schema_version == "1.0.0"


def test_audit_log_versioning_is_optional():
    """AuditLog versioning fields default to None for non-AI events."""
    log = AuditLog(log_id=uuid4(), request_id=uuid4(), actor="system", action="REQUEST_CLOSED")
    assert log.model_provider is None
    assert log.prompt_version is None


def test_entities_auto_populate_timestamps():
    """Entities set timezone-aware UTC timestamps automatically."""
    before = datetime.now(timezone.utc)
    session = UserSession(session_id=uuid4(), language=Language.ENGLISH)
    after = datetime.now(timezone.utc)
    assert before <= session.created_at <= after
    assert session.created_at.tzinfo is not None
