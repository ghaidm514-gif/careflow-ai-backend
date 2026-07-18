"""SQLAlchemy adapter for IStaffUserRepository."""

from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.ports import IStaffUserRepository
from app.domain.entities import StaffUser
from app.infrastructure.models import StaffUserModel
from app.infrastructure.repositories.mapping import staff_user_to_entity, staff_user_to_row


class SQLAlchemyStaffUserRepository(IStaffUserRepository):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def create(self, user: StaffUser) -> StaffUser:
        row = staff_user_to_row(user)
        self._session.add(row)
        await self._session.flush()
        return staff_user_to_entity(row)

    async def get_by_id(self, user_id: UUID) -> Optional[StaffUser]:
        row = await self._session.get(StaffUserModel, user_id)
        return staff_user_to_entity(row) if row else None

    async def get_by_email(self, email: str) -> Optional[StaffUser]:
        result = await self._session.execute(
            select(StaffUserModel).where(StaffUserModel.email == email)
        )
        row = result.scalar_one_or_none()
        return staff_user_to_entity(row) if row else None
