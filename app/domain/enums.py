"""Domain enums — No external dependencies."""

from enum import Enum


class Language(str, Enum):
    """Supported languages."""
    ENGLISH = "en"
    ARABIC = "ar"


class RequestStatus(str, Enum):
    """Service request lifecycle states."""
    PENDING = "pending"
    INTAKE_COMPLETE = "intake_complete"
    IN_TRIAGE = "in_triage"
    TRIAGE_COMPLETE = "triage_complete"
    SAFETY_ALERT = "safety_alert"
    AWAITING_RECOMMENDATION = "awaiting_recommendation"
    RECOMMENDATION_READY = "recommendation_ready"
    STAFF_REVIEW = "staff_review"
    CLOSED = "closed"


class RequestClassification(str, Enum):
    """Request classification outcomes."""
    ADMINISTRATIVE = "administrative"
    HEALTHCARE = "healthcare"
    UNCLEAR = "unclear"


class UrgencyLevel(str, Enum):
    """Triage urgency levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    EMERGENCY = "emergency"


class RecommendedService(str, Enum):
    """Recommended healthcare services."""
    ADMINISTRATIVE_SERVICE = "administrative_service"
    VIRTUAL_CONSULTATION = "virtual_consultation"
    PRIMARY_CARE = "primary_care"
    URGENT_CARE = "urgent_care"
    EMERGENCY_DEPARTMENT = "emergency_department"
    HUMAN_REVIEW = "human_review"


class SafetyFlagSeverity(str, Enum):
    """Safety flag severity levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class SafetyRuleCategory(str, Enum):
    """Safety rule category for future management."""
    EMERGENCY = "emergency"
    URGENT = "urgent"
    QUALITY = "quality"
    SYSTEM = "system"


class StaffDecisionType(str, Enum):
    """Staff decision types."""
    ACCEPT = "accept"
    MODIFY = "modify"
    ESCALATE = "escalate"
    CLOSE = "close"
    REFER = "refer"


class StaffRole(str, Enum):
    """Staff member roles."""
    TRIAGE_NURSE = "triage_nurse"
    ADMINISTRATOR = "administrator"
    SUPERVISOR = "supervisor"


class Permission(str, Enum):
    """Fine-grained permissions for RBAC."""
    VIEW_REQUEST = "view_request"
    ANSWER_TRIAGE = "answer_triage"
    ACCEPT_RECOMMENDATION = "accept_recommendation"
    MODIFY_RECOMMENDATION = "modify_recommendation"
    ESCALATE_REQUEST = "escalate_request"
    CLOSE_REQUEST = "close_request"
    VIEW_AUDIT_LOG = "view_audit_log"
    MANAGE_STAFF = "manage_staff"
