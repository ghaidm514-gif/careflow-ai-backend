"""Repository ports (interfaces) — Specific business operations, no generic CRUD."""

from abc import ABC, abstractmethod
from typing import Optional
from uuid import UUID

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
    async def list_by_session(self, session_id: UUID) -> list[ServiceRequest]:
        pass


class IConversationMessageRepository(ABC):
    """Conversation message repository (append-only; NO update/delete)."""

    @abstractmethod
    async def create(self, message: ConversationMessage) -> ConversationMessage:
        pass

    @abstractmethod
    async def list_by_request(self, request_id: UUID) -> list[ConversationMessage]:
        pass


class ITriageAnswerRepository(ABC):
    """Triage answer repository (append-only; NO update/delete)."""

    @abstractmethod
    async def create(self, answer: TriageAnswer) -> TriageAnswer:
        pass

    @abstractmethod
    async def list_by_request(self, request_id: UUID) -> list[TriageAnswer]:
        pass

    @abstractmethod
    async def get_by_request_and_question(
        self, request_id: UUID, question_id: str
    ) -> Optional[TriageAnswer]:
        pass


class ISafetyFlagRepository(ABC):
    """Safety flag repository (append-only; NO update/delete)."""

    @abstractmethod
    async def create(self, flag: SafetyFlag) -> SafetyFlag:
        pass

    @abstractmethod
    async def list_by_request(self, request_id: UUID) -> list[SafetyFlag]:
        pass


class IAIRecommendationRepository(ABC):
    """AI recommendation repository (append-only; NO update/delete).

    Regeneration adds a new row with the next sequence_number; prior rows are
    preserved for audit.
    """

    @abstractmethod
    async def add(self, rec: AIRecommendation) -> AIRecommendation:
        pass

    @abstractmethod
    async def get(self, recommendation_id: UUID) -> Optional[AIRecommendation]:
        pass

    @abstractmethod
    async def list_for_request(self, request_id: UUID) -> list[AIRecommendation]:
        pass

    @abstractmethod
    async def get_latest_for_request(self, request_id: UUID) -> Optional[AIRecommendation]:
        """Highest sequence_number for the request (deterministic)."""
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
    async def list_by_request(self, request_id: UUID) -> list[StaffDecision]:
        pass


class IAuditLogRepository(ABC):
    """Audit log repository (append-only; NO update/delete)."""

    @abstractmethod
    async def create(self, log: AuditLog) -> AuditLog:
        pass

    @abstractmethod
    async def list_by_request(self, request_id: UUID) -> list[AuditLog]:
        pass
