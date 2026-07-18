"""SQLAlchemy adapter for IConversationMessageRepository (append-only)."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.ports import IConversationMessageRepository
from app.domain.entities import ConversationMessage
from app.infrastructure.models import ConversationMessageModel
from app.infrastructure.repositories.mapping import message_to_entity, message_to_row


class SQLAlchemyConversationMessageRepository(IConversationMessageRepository):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def create(self, message: ConversationMessage) -> ConversationMessage:
        row = message_to_row(message)
        self._session.add(row)
        await self._session.flush()
        return message_to_entity(row)

    async def list_by_request(self, request_id: UUID) -> list[ConversationMessage]:
        result = await self._session.execute(
            select(ConversationMessageModel)
            .where(ConversationMessageModel.request_id == request_id)
            .order_by(ConversationMessageModel.created_at, ConversationMessageModel.message_id)
        )
        return [message_to_entity(row) for row in result.scalars()]
