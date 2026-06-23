"""Pydantic-схемы, связанные с заказами.

Схемы (в отличие от моделей SQLAlchemy) описывают форму данных на
границах системы — то, что приходит "снаружи" (от AI-агента, из
Telegram-сообщения, из будущего REST API) и что отдаётся "наружу".
Модели БД и схемы намеренно разные классы: модель — это таблица,
схема — это контракт данных, и они меняются по разным причинам.
"""

from pydantic import BaseModel, Field


class OrderCreateData(BaseModel):
    """Данные для создания заказа, извлечённые AI-агентом из чата."""

    client_full_name: str = Field(..., min_length=1, max_length=255)
    client_phone: str = Field(..., min_length=5, max_length=32)
    address: str = Field(..., min_length=1)
    carpet_count: int | None = Field(default=None, ge=0)
    notes: str | None = None
