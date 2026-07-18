"""SQLAlchemy adapter for IStaffDecisionRepository (append-only audit)."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.ports import IStaffDecisionRepository
from app.domain.entities import StaffDecision
from app.infrastructure.models import StaffDecisionModel
from app.infrastructure.repositories.mapping import decision_to_entity, decision_to_row


class SQLAlchemyStaffDecisionRepository(IStaffDecisionRepository):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def create(self, decision: StaffDecision) -> StaffDecision:
        row = decision_to_row(decision)
        self._session.add(row)
        await self._session.flush()
        return decision_to_entity(row)

    async def list_by_request(self, request_id: UUID) -> list[StaffDecision]:
        result = await self._session.execute(
            select(StaffDecisionModel)
            .where(StaffDecisionModel.request_id == request_id)
            .order_by(StaffDecisionModel.decided_at, StaffDecisionModel.decision_id)
        )
        return [decision_to_entity(row) for row in result.scalars()]
