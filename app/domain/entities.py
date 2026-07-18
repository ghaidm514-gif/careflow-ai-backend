"""Domain entities — Immutable or carefully mutable domain objects."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any
from uuid import UUID

from app.domain.enums import (
    Language,
    RequestStatus,
    RequestClassification,
    UrgencyLevel,
    RecommendedService,
    SafetyFlagSeverity,
    StaffDecisionType,
)


@dataclass(frozen=True)
class UserSession:
    """Immutable session record (frozen)."""
    session_id: UUID
    language: Language
    is_authenticated: bool = False
    staff_user_id: Optional[UUID] = None
    created_at: datetime = None

    def __post_init__(self):
        if self.created_at is None:
            object.__setattr__(self, "created_at", datetime.utcnow())


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
    created_at: datetime = None
    updated_at: datetime = None
    completed_at: Optional[datetime] = None

    def __post_init__(self):
        if self.created_at is None:
            object.__setattr__(self, "created_at", datetime.utcnow())
        if self.updated_at is None:
            object.__setattr__(self, "updated_at", datetime.utcnow())


@dataclass(frozen=True)
class ConversationMessage:
    """Immutable message (append-only)."""
    message_id: UUID
    request_id: UUID
    role: str
    content: str
    message_type: str
    created_at: datetime = None

    def __post_init__(self):
        if self.created_at is None:
            object.__setattr__(self, "created_at", datetime.utcnow())


@dataclass(frozen=True)
class TriageAnswer:
    """Immutable answer (append-only)."""
    answer_id: UUID
    request_id: UUID
    question_id: str
    question_text: str
    user_answer: str
    processed_at: datetime = None

    def __post_init__(self):
        if self.processed_at is None:
            object.__setattr__(self, "processed_at", datetime.utcnow())


@dataclass(frozen=True)
class SafetyFlag:
    """Immutable safety event (append-only)."""
    flag_id: UUID
    request_id: UUID
    rule_code: str
    severity: SafetyFlagSeverity
    description: str
    triggered_at: datetime = None
    action_taken: str = "HUMAN_REVIEW"

    def __post_init__(self):
        if self.triggered_at is None:
            object.__setattr__(self, "triggered_at", datetime.utcnow())


@dataclass
class AIRecommendation:
    """Mutable recommendation (can be regenerated; versioned)."""
    recommendation_id: UUID
    request_id: UUID
    recommended_service: RecommendedService
    urgency_level: UrgencyLevel
    rationale: str
    confidence: float
    confidence_reason: str
    rule_triggered: Optional[str] = None
    model_provider: str = "anthropic"
    model_name: str = "claude-3-5-sonnet-20241022"
    prompt_version: str = "1.0.0"
    workflow_version: str = "1.0.0"
    schema_version: str = "1.0.0"
    generated_at: datetime = None

    def __post_init__(self):
        if self.generated_at is None:
            object.__setattr__(self, "generated_at", datetime.utcnow())


@dataclass(frozen=True)
class StaffUser:
    """Immutable staff record (frozen)."""
    staff_user_id: UUID
    email: str
    role: str
    created_at: datetime = None

    def __post_init__(self):
        if self.created_at is None:
            object.__setattr__(self, "created_at", datetime.utcnow())


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
    decided_at: datetime = None

    def __post_init__(self):
        if self.decided_at is None:
            object.__setattr__(self, "decided_at", datetime.utcnow())


@dataclass(frozen=True)
class AuditLog:
    """Immutable audit record (append-only)."""
    log_id: UUID
    request_id: UUID
    actor: str
    action: str
    details: Optional[Dict[str, Any]] = None
    model_provider: Optional[str] = None
    model_name: Optional[str] = None
    prompt_version: Optional[str] = None
    workflow_version: Optional[str] = None
    schema_version: Optional[str] = None
    logged_at: datetime = None

    def __post_init__(self):
        if self.logged_at is None:
            object.__setattr__(self, "logged_at", datetime.utcnow())
