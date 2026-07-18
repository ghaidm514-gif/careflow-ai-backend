"""SQLAlchemy adapter for IUserSessionRepository."""

from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.ports import IUserSessionRepository
from app.domain.entities import UserSession
from app.infrastructure.models import UserSessionModel
from app.infrastructure.repositories.mapping import session_to_entity, session_to_row


class SQLAlchemyUserSessionRepository(IUserSessionRepository):
    """Adapter owns queries only; the caller owns the transaction."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def create(self, session: UserSession) -> UserSession:
        row = session_to_row(session)
        self._session.add(row)
        await self._session.flush()
        return session_to_entity(row)

    async def get_by_id(self, session_id: UUID) -> Optional[UserSession]:
        row = await self._session.get(UserSessionModel, session_id)
        return session_to_entity(row) if row else None
