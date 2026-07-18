"""Database configuration using SQLAlchemy 2.x."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Optional

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import DatabaseConfig

_engine: Optional[AsyncEngine] = None
_session_factory: Optional[async_sessionmaker[AsyncSession]] = None


def get_engine(config: DatabaseConfig) -> AsyncEngine:
    """Create or return the SQLAlchemy async engine (lazy)."""
    global _engine
    if _engine is None:
        database_url = config.database_url
        if database_url.startswith("postgresql://"):
            database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)

        _engine = create_async_engine(
            database_url,
            pool_pre_ping=True,
        )
    return _engine


def get_session_factory(config: DatabaseConfig) -> async_sessionmaker[AsyncSession]:
    """Create or return the async session factory (lazy)."""
    global _session_factory
    if _session_factory is None:
        engine = get_engine(config)
        _session_factory = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _session_factory


class DatabaseSession:
    """Database session context manager."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self.session_factory = session_factory

    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Yield a transaction-safe session that is always closed."""
        async with self.session_factory() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()


async def dispose_engine() -> None:
    """Dispose of the engine on application shutdown."""
    global _engine
    if _engine is not None:
        await _engine.dispose()
        _engine = None
