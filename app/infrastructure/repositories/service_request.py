"""SQLAlchemy adapter for IServiceRequestRepository."""

from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.ports import IServiceRequestRepository
from app.domain.entities import ServiceRequest
from app.domain.exceptions import ResourceNotFoundException
from app.infrastructure.models import ServiceRequestModel
from app.infrastructure.repositories.mapping import request_to_entity, request_to_row


class SQLAlchemyServiceRequestRepository(IServiceRequestRepository):
    """ServiceRequest is never deleted; closing is a status transition."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def create(self, request: ServiceRequest) -> ServiceRequest:
        row = request_to_row(request)
        self._session.add(row)
        await self._session.flush()
        return request_to_entity(row)

    async def get_by_id(self, request_id: UUID) -> Optional[ServiceRequest]:
        row = await self._session.get(ServiceRequestModel, request_id)
        return request_to_entity(row) if row else None

    async def update(self, request: ServiceRequest) -> ServiceRequest:
        row = await self._session.get(ServiceRequestModel, request.request_id)
        if row is None:
            raise ResourceNotFoundException(
                details={"resource_type": "service_request", "request_id": str(request.request_id)}
            )
        row.status = request.status
        row.classification = request.classification
        row.urgency_level = request.urgency_level
        row.recommended_service = request.recommended_service
        row.updated_at = request.updated_at
        row.completed_at = request.completed_at
        await self._session.flush()
        return request_to_entity(row)

    async def list_by_session(self, session_id: UUID) -> list[ServiceRequest]:
        result = await self._session.execute(
            select(ServiceRequestModel)
            .where(ServiceRequestModel.session_id == session_id)
            .order_by(ServiceRequestModel.created_at, ServiceRequestModel.request_id)
        )
        return [request_to_entity(row) for row in result.scalars()]
