"""SQLAlchemy adapter for IAuditLogRepository (append-only)."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.ports import IAuditLogRepository
from app.domain.entities import AuditLog
from app.infrastructure.models import AuditLogModel
from app.infrastructure.repositories.mapping import audit_to_entity, audit_to_row


class SQLAlchemyAuditLogRepository(IAuditLogRepository):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def create(self, log: AuditLog) -> AuditLog:
        row = audit_to_row(log)
        self._session.add(row)
        await self._session.flush()
        return audit_to_entity(row)

    async def list_by_request(self, request_id: UUID) -> list[AuditLog]:
        result = await self._session.execute(
            select(AuditLogModel)
            .where(AuditLogModel.request_id == request_id)
            .order_by(AuditLogModel.logged_at, AuditLogModel.log_id)
        )
        return [audit_to_entity(row) for row in result.scalars()]
