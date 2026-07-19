"""FastAPI dependencies: DB session, repositories, triage service."""

from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.triage_service import Repos, TriageService
from app.config import load_settings
from app.infrastructure.database import get_session_factory
from app.infrastructure.llm import build_llm_provider
from app.infrastructure.repositories import (
    SQLAlchemyAIRecommendationRepository,
    SQLAlchemyAuditLogRepository,
    SQLAlchemyConversationMessageRepository,
    SQLAlchemySafetyFlagRepository,
    SQLAlchemyServiceRequestRepository,
    SQLAlchemyTriageAnswerRepository,
    SQLAlchemyUserSessionRepository,
)
from app.safety.engine import SafetyEngine


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """One session per request; the endpoint owns commit/rollback."""
    settings = load_settings()
    factory = get_session_factory(settings.database)
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def get_triage_service(session: Annotated[AsyncSession, Depends(get_db)]) -> TriageService:
    settings = load_settings()
    repos = Repos(
        sessions=SQLAlchemyUserSessionRepository(session),
        requests=SQLAlchemyServiceRequestRepository(session),
        messages=SQLAlchemyConversationMessageRepository(session),
        answers=SQLAlchemyTriageAnswerRepository(session),
        flags=SQLAlchemySafetyFlagRepository(session),
        recommendations=SQLAlchemyAIRecommendationRepository(session),
        audits=SQLAlchemyAuditLogRepository(session),
    )
    return TriageService(
        repos=repos,
        llm=build_llm_provider(settings.llm.llm_provider),
        safety=SafetyEngine(),
        max_questions=settings.triage.max_triage_questions,
    )
