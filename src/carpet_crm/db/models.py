"""Модели предметной области: клиенты и заказы.

Структура на этом этапе сознательно простая (см. README раздел
"Решения по архитектуре"): количество ковров хранится как одно число
на заказе, а не как отдельная таблица позиций. Когда появится
расчёт стоимости по типу/размеру ковра, потребуется миграция,
выносящая позиции в отдельную таблицу OrderItem — это нормальный
рост схемы через Alembic, а не признак "неправильного" MVP.
"""

from sqlalchemy import BigInteger, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.carpet_crm.db.base import Base, TimestampMixin
from src.carpet_crm.db.enums import OrderStatus


class Client(Base, TimestampMixin):
    """Клиент мойки ковров.

    Вынесен в отдельную таблицу (а не просто поля внутри Order),
    чтобы у одного клиента можно было видеть историю всех его
    заказов — это нужно уже на этапе MVP для ответа на вопрос
    "когда этот клиент обращался в прошлый раз".
    """

    __tablename__ = "clients"

    id: Mapped[int] = mapped_column(primary_key=True)

    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str] = mapped_column(String(32), nullable=False, unique=True, index=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    """Основной адрес. Конкретный заказ может иметь другой адрес
    (Order.address) — например, клиент заказывает мойку для родственника.
    """

    orders: Mapped[list["Order"]] = relationship(back_populates="client")

    def __repr__(self) -> str:
        return f"Client(id={self.id}, full_name={self.full_name!r}, phone={self.phone!r})"


class Order(Base, TimestampMixin):
    """Заказ на мойку ковров — центральная сущность системы."""

    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)

    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"), nullable=False, index=True)
    client: Mapped["Client"] = relationship(back_populates="orders")

    status: Mapped[OrderStatus] = mapped_column(
        String(20),
        default=OrderStatus.NEW,
        nullable=False,
        index=True,
    )
    """Храним как String, а не нативный PostgreSQL ENUM.

    Нативный ENUM в PostgreSQL технически чуть строже (база сама
    отвергнет недопустимое значение), но добавление нового статуса
    в будущем требует отдельной ALTER TYPE миграции с известными
    сложностями в Alembic. String + валидация на уровне Pydantic-схем
    даёт почти ту же надёжность при намного более простых миграциях —
    разумный компромисс для проекта на этой стадии.
    """

    address: Mapped[str] = mapped_column(Text, nullable=False)
    """Адрес, откуда забирают ковры по этому заказу."""

    carpet_count: Mapped[int | None] = mapped_column(nullable=True)
    """Количество ковров. Nullable, потому что на этапе NEW (заказ
    создан со слов оператора) точное количество может быть неизвестно —
    его подтверждает доставка при статусе PICKED_UP.
    """

    estimated_price: Mapped[Numeric | None] = mapped_column(Numeric(10, 2), nullable=True)
    """Предварительная стоимость. Поле заложено сейчас, хотя расчёт
    стоимости — фича следующей итерации, чтобы не делать миграцию
    повторно ради одного числового столбца.
    """

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    """Свободные заметки: особенности ковра, договорённости с клиентом и т.п."""

    created_by_chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    """Telegram chat_id оператора, создавшего заказ — для аудита
    "кто и когда" без необходимости в отдельной таблице пользователей
    на этом этапе.
    """

    def __repr__(self) -> str:
        return f"Order(id={self.id}, status={self.status!r}, client_id={self.client_id})"
