"""SQLAlchemy adapter for IAIRecommendationRepository (append-only).

Frozen D-003: regeneration adds a new row with the next sequence_number; the
current recommendation is the highest sequence_number (deterministic).
"""

from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.ports import IAIRecommendationRepository
from app.domain.entities import AIRecommendation
from app.infrastructure.models import AIRecommendationModel
from app.infrastructure.repositories.mapping import (
    recommendation_to_entity,
    recommendation_to_row,
)


class SQLAlchemyAIRecommendationRepository(IAIRecommendationRepository):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def add(self, rec: AIRecommendation) -> AIRecommendation:
        row = recommendation_to_row(rec)
        self._session.add(row)
        await self._session.flush()
        return recommendation_to_entity(row)

    async def get(self, recommendation_id: UUID) -> Optional[AIRecommendation]:
        row = await self._session.get(AIRecommendationModel, recommendation_id)
        return recommendation_to_entity(row) if row else None

    async def list_for_request(self, request_id: UUID) -> list[AIRecommendation]:
        result = await self._session.execute(
            select(AIRecommendationModel)
            .where(AIRecommendationModel.request_id == request_id)
            .order_by(AIRecommendationModel.sequence_number)
        )
        return [recommendation_to_entity(row) for row in result.scalars()]

    async def get_latest_for_request(self, request_id: UUID) -> Optional[AIRecommendation]:
        result = await self._session.execute(
            select(AIRecommendationModel)
            .where(AIRecommendationModel.request_id == request_id)
            .order_by(AIRecommendationModel.sequence_number.desc())
            .limit(1)
        )
        row = result.scalar_one_or_none()
        return recommendation_to_entity(row) if row else None
