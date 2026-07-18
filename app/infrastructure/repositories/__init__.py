"""SQLAlchemy repository adapters for the frozen application ports."""

from app.infrastructure.repositories.ai_recommendation import (
    SQLAlchemyAIRecommendationRepository,
)
from app.infrastructure.repositories.audit_log import SQLAlchemyAuditLogRepository
from app.infrastructure.repositories.conversation_message import (
    SQLAlchemyConversationMessageRepository,
)
from app.infrastructure.repositories.safety_flag import SQLAlchemySafetyFlagRepository
from app.infrastructure.repositories.service_request import (
    SQLAlchemyServiceRequestRepository,
)
from app.infrastructure.repositories.staff_decision import (
    SQLAlchemyStaffDecisionRepository,
)
from app.infrastructure.repositories.staff_user import SQLAlchemyStaffUserRepository
from app.infrastructure.repositories.triage_answer import SQLAlchemyTriageAnswerRepository
from app.infrastructure.repositories.user_session import SQLAlchemyUserSessionRepository

__all__ = [
    "SQLAlchemyAIRecommendationRepository",
    "SQLAlchemyAuditLogRepository",
    "SQLAlchemyConversationMessageRepository",
    "SQLAlchemySafetyFlagRepository",
    "SQLAlchemyServiceRequestRepository",
    "SQLAlchemyStaffDecisionRepository",
    "SQLAlchemyStaffUserRepository",
    "SQLAlchemyTriageAnswerRepository",
    "SQLAlchemyUserSessionRepository",
]
