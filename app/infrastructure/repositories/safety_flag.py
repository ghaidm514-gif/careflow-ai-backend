"""SQLAlchemy adapter for ISafetyFlagRepository (append-only)."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.ports import ISafetyFlagRepository
from app.domain.entities import SafetyFlag
from app.infrastructure.models import SafetyFlagModel
from app.infrastructure.repositories.mapping import flag_to_entity, flag_to_row


class SQLAlchemySafetyFlagRepository(ISafetyFlagRepository):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def create(self, flag: SafetyFlag) -> SafetyFlag:
        row = flag_to_row(flag)
        self._session.add(row)
        await self._session.flush()
        return flag_to_entity(row)

    async def list_by_request(self, request_id: UUID) -> list[SafetyFlag]:
        result = await self._session.execute(
            select(SafetyFlagModel)
            .where(SafetyFlagModel.request_id == request_id)
            .order_by(SafetyFlagModel.triggered_at, SafetyFlagModel.flag_id)
        )
        return [flag_to_entity(row) for row in result.scalars()]
