"""Domain entities — Immutable or carefully mutable domain objects."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

from app.domain.enums import (
    Language,
    RecommendedService,
    RequestClassification,
    RequestStatus,
    SafetyFlagSeverity,
    StaffDecisionType,
    UrgencyLevel,
)


def utc_now() -> datetime:
    """Timezone-aware UTC timestamp."""
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class UserSession:
    """Immutable session record (frozen)."""

    session_id: UUID
    language: Language
    is_authenticated: bool = False
    staff_user_id: Optional[UUID] = None
    created_at: datetime = field(default_factory=utc_now)


@dataclass
class ServiceRequest:
    """Mutable request during workflow."""

    request_id: UUID
    session_id: UUID
    initial_description: str
    language: Language
    status: RequestStatus
    classification: Optional[RequestClassification] = None
    urgency_level: Optional[UrgencyLevel] = None
    recommended_service: Optional[RecommendedService] = None
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
    completed_at: Optional[datetime] = None


@dataclass(frozen=True)
class ConversationMessage:
    """Immutable message (append-only)."""

    message_id: UUID
    request_id: UUID
    role: str
    content: str
    message_type: str
    created_at: datetime = field(default_factory=utc_now)


@dataclass(frozen=True)
class TriageAnswer:
    """Immutable answer (append-only)."""

    answer_id: UUID
    request_id: UUID
    question_id: str
    question_text: str
    user_answer: str
    processed_at: datetime = field(default_factory=utc_now)


@dataclass(frozen=True)
class SafetyFlag:
    """Immutable safety event (append-only)."""

    flag_id: UUID
    request_id: UUID
    rule_code: str
    severity: SafetyFlagSeverity
    description: str
    action_taken: str = "HUMAN_REVIEW"
    triggered_at: datetime = field(default_factory=utc_now)


@dataclass(frozen=True)
class AIRecommendation:
    """Immutable recommendation (append-only; regeneration creates a new row).

    sequence_number orders regenerations for a request; the highest number is
    the current recommendation. Prior rows remain for audit.
    """

    recommendation_id: UUID
    request_id: UUID
    recommended_service: RecommendedService
    urgency_level: UrgencyLevel
    rationale: str
    confidence: float
    confidence_reason: str
    sequence_number: int = 1
    rule_triggered: Optional[str] = None
    model_provider: str = "anthropic"
    model_name: str = "claude-3-5-sonnet-20241022"
    prompt_version: str = "1.0.0"
    workflow_version: str = "1.0.0"
    schema_version: str = "1.0.0"
    generated_at: datetime = field(default_factory=utc_now)


@dataclass(frozen=True)
class StaffUser:
    """Immutable staff record (frozen)."""

    staff_user_id: UUID
    email: str
    role: str
    created_at: datetime = field(default_factory=utc_now)


@dataclass(frozen=True)
class StaffDecision:
    """Immutable decision (append-only audit)."""

    decision_id: UUID
    request_id: UUID
    staff_user_id: UUID
    decision_type: StaffDecisionType
    notes: Optional[str] = None
    modified_service: Optional[RecommendedService] = None
    modified_urgency: Optional[UrgencyLevel] = None
    reason: Optional[str] = None
    decided_at: datetime = field(default_factory=utc_now)


@dataclass(frozen=True)
class AuditLog:
    """Immutable audit record (append-only)."""

    log_id: UUID
    request_id: UUID
    actor: str
    action: str
    details: Optional[dict[str, Any]] = None
    model_provider: Optional[str] = None
    model_name: Optional[str] = None
    prompt_version: Optional[str] = None
    workflow_version: Optional[str] = None
    schema_version: Optional[str] = None
    logged_at: datetime = field(default_factory=utc_now)
