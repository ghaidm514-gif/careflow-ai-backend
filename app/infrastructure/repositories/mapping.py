"""ORM row ⇄ frozen domain dataclass conversion.

ORM types never cross the repository-port boundary: adapters accept and return
domain entities only. StaffUser.role is the single type conversion (domain str
⇄ ORM StaffRole enum, by value).

Timestamps: the domain invariant is timezone-aware UTC. PostgreSQL timestamptz
round-trips aware datetimes; SQLite (local verification only) drops tzinfo, so
_aware() restores UTC on the read path. Values are always written as UTC.
"""

from datetime import datetime, timezone
from typing import Optional

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
from app.domain.enums import StaffRole
from app.infrastructure.models import (
    AIRecommendationModel,
    AuditLogModel,
    ConversationMessageModel,
    SafetyFlagModel,
    ServiceRequestModel,
    StaffDecisionModel,
    StaffUserModel,
    TriageAnswerModel,
    UserSessionModel,
)


def _aware(dt: datetime) -> datetime:
    """Restore UTC tzinfo lost by dialects without timezone storage (SQLite)."""
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


def _aware_opt(dt: Optional[datetime]) -> Optional[datetime]:
    return None if dt is None else _aware(dt)


def session_to_entity(row: UserSessionModel) -> UserSession:
    return UserSession(
        session_id=row.session_id,
        language=row.language,
        is_authenticated=row.is_authenticated,
        staff_user_id=row.staff_user_id,
        created_at=_aware(row.created_at),
    )


def session_to_row(entity: UserSession) -> UserSessionModel:
    return UserSessionModel(
        session_id=entity.session_id,
        language=entity.language,
        is_authenticated=entity.is_authenticated,
        staff_user_id=entity.staff_user_id,
        created_at=entity.created_at,
    )


def request_to_entity(row: ServiceRequestModel) -> ServiceRequest:
    return ServiceRequest(
        request_id=row.request_id,
        session_id=row.session_id,
        initial_description=row.initial_description,
        language=row.language,
        status=row.status,
        classification=row.classification,
        urgency_level=row.urgency_level,
        recommended_service=row.recommended_service,
        created_at=_aware(row.created_at),
        updated_at=_aware(row.updated_at),
        completed_at=_aware_opt(row.completed_at),
    )


def request_to_row(entity: ServiceRequest) -> ServiceRequestModel:
    return ServiceRequestModel(
        request_id=entity.request_id,
        session_id=entity.session_id,
        initial_description=entity.initial_description,
        language=entity.language,
        status=entity.status,
        classification=entity.classification,
        urgency_level=entity.urgency_level,
        recommended_service=entity.recommended_service,
        created_at=entity.created_at,
        updated_at=entity.updated_at,
        completed_at=entity.completed_at,
    )


def message_to_entity(row: ConversationMessageModel) -> ConversationMessage:
    return ConversationMessage(
        message_id=row.message_id,
        request_id=row.request_id,
        role=row.role,
        content=row.content,
        message_type=row.message_type,
        created_at=_aware(row.created_at),
    )


def message_to_row(entity: ConversationMessage) -> ConversationMessageModel:
    return ConversationMessageModel(
        message_id=entity.message_id,
        request_id=entity.request_id,
        role=entity.role,
        content=entity.content,
        message_type=entity.message_type,
        created_at=entity.created_at,
    )


def answer_to_entity(row: TriageAnswerModel) -> TriageAnswer:
    return TriageAnswer(
        answer_id=row.answer_id,
        request_id=row.request_id,
        question_id=row.question_id,
        question_text=row.question_text,
        user_answer=row.user_answer,
        processed_at=_aware(row.processed_at),
    )


def answer_to_row(entity: TriageAnswer) -> TriageAnswerModel:
    return TriageAnswerModel(
        answer_id=entity.answer_id,
        request_id=entity.request_id,
        question_id=entity.question_id,
        question_text=entity.question_text,
        user_answer=entity.user_answer,
        processed_at=entity.processed_at,
    )


def flag_to_entity(row: SafetyFlagModel) -> SafetyFlag:
    return SafetyFlag(
        flag_id=row.flag_id,
        request_id=row.request_id,
        rule_code=row.rule_code,
        severity=row.severity,
        description=row.description,
        action_taken=row.action_taken,
        triggered_at=_aware(row.triggered_at),
    )


def flag_to_row(entity: SafetyFlag) -> SafetyFlagModel:
    return SafetyFlagModel(
        flag_id=entity.flag_id,
        request_id=entity.request_id,
        rule_code=entity.rule_code,
        severity=entity.severity,
        description=entity.description,
        action_taken=entity.action_taken,
        triggered_at=entity.triggered_at,
    )


def recommendation_to_entity(row: AIRecommendationModel) -> AIRecommendation:
    return AIRecommendation(
        recommendation_id=row.recommendation_id,
        request_id=row.request_id,
        recommended_service=row.recommended_service,
        urgency_level=row.urgency_level,
        rationale=row.rationale,
        confidence=row.confidence,
        confidence_reason=row.confidence_reason,
        rule_triggered=row.rule_triggered,
        sequence_number=row.sequence_number,
        model_provider=row.model_provider,
        model_name=row.model_name,
        prompt_version=row.prompt_version,
        workflow_version=row.workflow_version,
        schema_version=row.schema_version,
        generated_at=_aware(row.generated_at),
    )


def recommendation_to_row(entity: AIRecommendation) -> AIRecommendationModel:
    return AIRecommendationModel(
        recommendation_id=entity.recommendation_id,
        request_id=entity.request_id,
        recommended_service=entity.recommended_service,
        urgency_level=entity.urgency_level,
        rationale=entity.rationale,
        confidence=entity.confidence,
        confidence_reason=entity.confidence_reason,
        rule_triggered=entity.rule_triggered,
        sequence_number=entity.sequence_number,
        model_provider=entity.model_provider,
        model_name=entity.model_name,
        prompt_version=entity.prompt_version,
        workflow_version=entity.workflow_version,
        schema_version=entity.schema_version,
        generated_at=entity.generated_at,
    )


def staff_user_to_entity(row: StaffUserModel) -> StaffUser:
    return StaffUser(
        staff_user_id=row.staff_user_id,
        email=row.email,
        role=row.role.value,
        created_at=_aware(row.created_at),
    )


def staff_user_to_row(entity: StaffUser) -> StaffUserModel:
    return StaffUserModel(
        staff_user_id=entity.staff_user_id,
        email=entity.email,
        role=StaffRole(entity.role),
        created_at=entity.created_at,
    )


def decision_to_entity(row: StaffDecisionModel) -> StaffDecision:
    return StaffDecision(
        decision_id=row.decision_id,
        request_id=row.request_id,
        staff_user_id=row.staff_user_id,
        decision_type=row.decision_type,
        notes=row.notes,
        modified_service=row.modified_service,
        modified_urgency=row.modified_urgency,
        reason=row.reason,
        decided_at=_aware(row.decided_at),
    )


def decision_to_row(entity: StaffDecision) -> StaffDecisionModel:
    return StaffDecisionModel(
        decision_id=entity.decision_id,
        request_id=entity.request_id,
        staff_user_id=entity.staff_user_id,
        decision_type=entity.decision_type,
        notes=entity.notes,
        modified_service=entity.modified_service,
        modified_urgency=entity.modified_urgency,
        reason=entity.reason,
        decided_at=entity.decided_at,
    )


def audit_to_entity(row: AuditLogModel) -> AuditLog:
    return AuditLog(
        log_id=row.log_id,
        request_id=row.request_id,
        actor=row.actor,
        action=row.action,
        details=row.details,
        model_provider=row.model_provider,
        model_name=row.model_name,
        prompt_version=row.prompt_version,
        workflow_version=row.workflow_version,
        schema_version=row.schema_version,
        logged_at=_aware(row.logged_at),
    )


def audit_to_row(entity: AuditLog) -> AuditLogModel:
    return AuditLogModel(
        log_id=entity.log_id,
        request_id=entity.request_id,
        actor=entity.actor,
        action=entity.action,
        details=entity.details,
        model_provider=entity.model_provider,
        model_name=entity.model_name,
        prompt_version=entity.prompt_version,
        workflow_version=entity.workflow_version,
        schema_version=entity.schema_version,
        logged_at=entity.logged_at,
    )
