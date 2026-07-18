"""Repository ports (interfaces) — Specific business operations, no generic CRUD."""

from abc import ABC, abstractmethod
from typing import List, Optional
from uuid import UUID

from app.domain.entities import (
    UserSession, ServiceRequest, ConversationMessage, TriageAnswer,
    SafetyFlag, AIRecommendation, StaffUser, StaffDecision, AuditLog,
)


class IUserSessionRepository(ABC):
    """User/patient session repository."""
    @abstractmethod
    async def create(self, session: UserSession) -> UserSession:
        pass

    @abstractmethod
    async def get_by_id(self, session_id: UUID) -> Optional[UserSession]:
        pass


class IServiceRequestRepository(ABC):
    """Service request repository."""
    @abstractmethod
    async def create(self, request: ServiceRequest) -> ServiceRequest:
        pass

    @abstractmethod
    async def get_by_id(self, request_id: UUID) -> Optional[ServiceRequest]:
        pass

    @abstractmethod
    async def update(self, request: ServiceRequest) -> ServiceRequest:
        pass

    @abstractmethod
    async def list_by_session(self, session_id: UUID) -> List[ServiceRequest]:
        pass


class IConversationMessageRepository(ABC):
    """Conversation message repository (append-only; NO update/delete)."""
    @abstractmethod
    async def create(self, message: ConversationMessage) -> ConversationMessage:
        pass

    @abstractmethod
    async def list_by_request(self, request_id: UUID) -> List[ConversationMessage]:
        pass


class ITriageAnswerRepository(ABC):
    """Triage answer repository (append-only; NO update/delete)."""
    @abstractmethod
    async def create(self, answer: TriageAnswer) -> TriageAnswer:
        pass

    @abstractmethod
    async def list_by_request(self, request_id: UUID) -> List[TriageAnswer]:
        pass

    @abstractmethod
    async def get_by_request_and_question(self, request_id: UUID, question_id: str) -> Optional[TriageAnswer]:
        pass


class ISafetyFlagRepository(ABC):
    """Safety flag repository (append-only; NO update/delete)."""
    @abstractmethod
    async def create(self, flag: SafetyFlag) -> SafetyFlag:
        pass

    @abstractmethod
    async def list_by_request(self, request_id: UUID) -> List[SafetyFlag]:
        pass


class IAIRecommendationRepository(ABC):
    """AI recommendation repository (one per request; NO delete)."""
    @abstractmethod
    async def create(self, rec: AIRecommendation) -> AIRecommendation:
        pass

    @abstractmethod
    async def get_by_request_id(self, request_id: UUID) -> Optional[AIRecommendation]:
        pass

    @abstractmethod
    async def update(self, rec: AIRecommendation) -> AIRecommendation:
        pass


class IStaffUserRepository(ABC):
    """Staff user repository."""
    @abstractmethod
    async def create(self, user: StaffUser) -> StaffUser:
        pass

    @abstractmethod
    async def get_by_id(self, user_id: UUID) -> Optional[StaffUser]:
        pass

    @abstractmethod
    async def get_by_email(self, email: str) -> Optional[StaffUser]:
        pass


class IStaffDecisionRepository(ABC):
    """Staff decision repository (append-only audit; NO delete)."""
    @abstractmethod
    async def create(self, decision: StaffDecision) -> StaffDecision:
        pass

    @abstractmethod
    async def list_by_request(self, request_id: UUID) -> List[StaffDecision]:
        pass


class IAuditLogRepository(ABC):
    """Audit log repository (append-only; NO update/delete)."""
    @abstractmethod
    async def create(self, log: AuditLog) -> AuditLog:
        pass

    @abstractmethod
    async def list_by_request(self, request_id: UUID) -> List[AuditLog]:
        pass
