"""Базовые классы для моделей SQLAlchemy."""

from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Базовый класс, от которого наследуются все модели БД.

    Используем DeclarativeBase (новый стиль SQLAlchemy 2.0) вместо
    устаревшего declarative_base() — это даёт корректную поддержку
    type hints (Mapped[...]) и автодополнение в IDE.
    """


class TimestampMixin:
    """Миксин, добавляющий поля created_at/updated_at любой модели.

    Любая таблица, где важно знать "когда создано" и "когда изменено"
    (а это почти все таблицы в нашем проекте), просто наследует этот
    миксин вместо дублирования двух одинаковых полей в каждой модели.
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
