"""Подключение к базе данных: асинхронный движок и фабрика сессий.

Этот модуль — единственное место в проекте, где создаётся SQLAlchemy
Engine. Репозитории и остальной код получают сессии через
get_db_session(), а не создают своё собственное подключение —
это гарантирует, что во всём приложении используется один и тот же
пул соединений с базой.
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from carpet_crm.core.config import get_settings

settings = get_settings()

engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
)

async_session_factory = async_sessionmaker(
    engine,
    expire_on_commit=False,
)


async def get_db_session() -> AsyncGenerator[AsyncSession]:
    """FastAPI-зависимость (Depends), отдающая одну сессию на запрос."""
    async with async_session_factory() as session:
        yield session
