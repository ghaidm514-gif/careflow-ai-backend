"""SQLAlchemy ORM models — infrastructure layer only.

Mapped 1:1 from the frozen Phase 2 domain entities. Domain code never imports
this module; repositories (Step 3.2) translate between ORM rows and domain
dataclasses.

Type portability:
- Uuid: native UUID on PostgreSQL, CHAR(32) on SQLite.
- Enum columns: VARCHAR + CHECK constraint (native_enum=False) so migrations
  stay portable and enum-value changes do not require ALTER TYPE.
- JSON: plain JSON with a JSONB variant on PostgreSQL.
Append-only tables (conversation_messages, triage_answers, safety_flags,
staff_decisions, audit_logs) are additionally protected by PostgreSQL triggers
added in the initial migration (dialect-guarded); on other dialects the
repository-port layer is the enforcement boundary.
"""

import uuid
from datetime import datetime, timezone
from enum import Enum as PyEnum
from typing import Any, Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import JSON

from app.domain.enums import (
    Language,
    RecommendedService,
    RequestClassification,
    RequestStatus,
    SafetyFlagSeverity,
    StaffDecisionType,
    StaffRole,
    UrgencyLevel,
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


PortableJSON = JSON().with_variant(JSONB(), "postgresql")


def _enum_values(enum_cls: type[PyEnum]) -> list[str]:
    return [str(member.value) for member in enum_cls]


def enum_column(enum_cls: type[PyEnum], name: str) -> Enum:
    """VARCHAR + CHECK enum column, portable across dialects."""
    return Enum(
        enum_cls,
        name=name,
        native_enum=False,
        values_callable=_enum_values,
        length=50,
    )


class Base(DeclarativeBase):
    pass


class UserSessionModel(Base):
    __tablename__ = "user_sessions"

    session_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    language: Mapped[Language] = mapped_column(enum_column(Language, "language"), nullable=False)
    is_authenticated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    staff_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("staff_users.staff_user_id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )

    __table_args__ = (
        Index("ix_user_sessions_created_at", "created_at"),
        Index("ix_user_sessions_staff_user_id", "staff_user_id"),
    )


class ServiceRequestModel(Base):
    __tablename__ = "service_requests"

    request_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("user_sessions.session_id", ondelete="CASCADE"), nullable=False
    )
    initial_description: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[Language] = mapped_column(
        enum_column(Language, "request_language"), nullable=False
    )
    status: Mapped[RequestStatus] = mapped_column(
        enum_column(RequestStatus, "request_status"),
        nullable=False,
        default=RequestStatus.PENDING,
    )
    classification: Mapped[Optional[RequestClassification]] = mapped_column(
        enum_column(RequestClassification, "request_classification"), nullable=True
    )
    urgency_level: Mapped[Optional[UrgencyLevel]] = mapped_column(
        enum_column(UrgencyLevel, "urgency_level"), nullable=True
    )
    recommended_service: Mapped[Optional[RecommendedService]] = mapped_column(
        enum_column(RecommendedService, "recommended_service"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_service_requests_session_id", "session_id"),
        Index("ix_service_requests_status", "status"),
        Index("ix_service_requests_created_at", "created_at"),
    )


class ConversationMessageModel(Base):
    """Append-only."""

    __tablename__ = "conversation_messages"

    message_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    request_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("service_requests.request_id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    message_type: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )

    __table_args__ = (
        CheckConstraint("role IN ('user', 'assistant', 'system')", name="ck_messages_role"),
        Index("ix_conversation_messages_request_id", "request_id"),
        Index("ix_conversation_messages_created_at", "created_at"),
    )


class TriageAnswerModel(Base):
    """Append-only. One active answer per (request, question)."""

    __tablename__ = "triage_answers"

    answer_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    request_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("service_requests.request_id", ondelete="CASCADE"), nullable=False
    )
    question_id: Mapped[str] = mapped_column(String(100), nullable=False)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    user_answer: Mapped[str] = mapped_column(Text, nullable=False)
    processed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )

    __table_args__ = (
        UniqueConstraint("request_id", "question_id", name="uq_triage_answers_request_question"),
        Index("ix_triage_answers_request_id", "request_id"),
    )


class SafetyFlagModel(Base):
    """Append-only."""

    __tablename__ = "safety_flags"

    flag_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    request_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("service_requests.request_id", ondelete="CASCADE"), nullable=False
    )
    rule_code: Mapped[str] = mapped_column(String(100), nullable=False)
    severity: Mapped[SafetyFlagSeverity] = mapped_column(
        enum_column(SafetyFlagSeverity, "safety_flag_severity"), nullable=False
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    action_taken: Mapped[str] = mapped_column(String(100), nullable=False)
    triggered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )

    __table_args__ = (
        Index("ix_safety_flags_request_id", "request_id"),
        Index("ix_safety_flags_severity", "severity"),
        Index("ix_safety_flags_rule_code", "rule_code"),
    )


class AIRecommendationModel(Base):
    """Append-only: regeneration inserts a new row with the next sequence_number."""

    __tablename__ = "ai_recommendations"

    recommendation_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    request_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("service_requests.request_id", ondelete="CASCADE"),
        nullable=False,
    )
    sequence_number: Mapped[int] = mapped_column(nullable=False, default=1)
    recommended_service: Mapped[RecommendedService] = mapped_column(
        enum_column(RecommendedService, "rec_recommended_service"), nullable=False
    )
    urgency_level: Mapped[UrgencyLevel] = mapped_column(
        enum_column(UrgencyLevel, "rec_urgency_level"), nullable=False
    )
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    confidence_reason: Mapped[str] = mapped_column(Text, nullable=False)
    rule_triggered: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    model_provider: Mapped[str] = mapped_column(String(50), nullable=False)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(20), nullable=False)
    workflow_version: Mapped[str] = mapped_column(String(20), nullable=False)
    schema_version: Mapped[str] = mapped_column(String(20), nullable=False)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )

    __table_args__ = (
        CheckConstraint(
            "confidence >= 0.0 AND confidence <= 1.0", name="ck_recommendations_confidence"
        ),
        UniqueConstraint(
            "request_id", "sequence_number", name="uq_ai_recommendations_request_sequence"
        ),
        Index("ix_ai_recommendations_request_id", "request_id"),
        Index("ix_ai_recommendations_generated_at", "generated_at"),
    )


class StaffUserModel(Base):
    __tablename__ = "staff_users"

    staff_user_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    role: Mapped[StaffRole] = mapped_column(enum_column(StaffRole, "staff_role"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )

    __table_args__ = (Index("ix_staff_users_role", "role"),)


class StaffDecisionModel(Base):
    """Append-only audit record."""

    __tablename__ = "staff_decisions"

    decision_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    request_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("service_requests.request_id", ondelete="CASCADE"), nullable=False
    )
    staff_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("staff_users.staff_user_id", ondelete="RESTRICT"), nullable=False
    )
    decision_type: Mapped[StaffDecisionType] = mapped_column(
        enum_column(StaffDecisionType, "staff_decision_type"), nullable=False
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    modified_service: Mapped[Optional[RecommendedService]] = mapped_column(
        enum_column(RecommendedService, "decision_modified_service"), nullable=True
    )
    modified_urgency: Mapped[Optional[UrgencyLevel]] = mapped_column(
        enum_column(UrgencyLevel, "decision_modified_urgency"), nullable=True
    )
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    decided_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )

    __table_args__ = (
        Index("ix_staff_decisions_request_id", "request_id"),
        Index("ix_staff_decisions_staff_user_id", "staff_user_id"),
        Index("ix_staff_decisions_decided_at", "decided_at"),
    )


class AuditLogModel(Base):
    """Append-only."""

    __tablename__ = "audit_logs"

    log_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    request_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("service_requests.request_id", ondelete="CASCADE"), nullable=False
    )
    actor: Mapped[str] = mapped_column(String(100), nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    details: Mapped[Optional[dict[str, Any]]] = mapped_column(PortableJSON, nullable=True)
    model_provider: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    model_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    prompt_version: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    workflow_version: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    schema_version: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    logged_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )

    __table_args__ = (
        Index("ix_audit_logs_request_id", "request_id"),
        Index("ix_audit_logs_logged_at", "logged_at"),
        Index("ix_audit_logs_action", "action"),
    )


APPEND_ONLY_TABLES = (
    "ai_recommendations",
    "conversation_messages",
    "triage_answers",
    "safety_flags",
    "staff_decisions",
    "audit_logs",
)
