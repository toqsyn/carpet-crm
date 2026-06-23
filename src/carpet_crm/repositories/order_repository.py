"""Репозиторий для модели Order."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from carpet_crm.db.enums import OrderStatus
from carpet_crm.db.models import Order


class OrderRepository:
    """Доступ к данным заказов в базе данных."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, order_id: int) -> Order | None:
        """Возвращает заказ по ID вместе с данными клиента (selectinload)."""
        statement = (
            select(Order).where(Order.id == order_id).options(selectinload(Order.client))
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def list_by_status(self, status: OrderStatus) -> list[Order]:
        """Возвращает все заказы с указанным статусом."""
        statement = (
            select(Order).where(Order.status == status).options(selectinload(Order.client))
        )
        result = await self._session.execute(statement)
        return list(result.scalars().all())

    async def create(
        self,
        *,
        client_id: int,
        address: str,
        created_by_chat_id: int,
        carpet_count: int | None = None,
        notes: str | None = None,
        ) -> Order:
        """Создаёт новый заказ со статусом NEW.

        После flush() выполняется refresh() с явным attribute_names,
        который подгружает relationship `client` сразу, в той же
        async-сессии. Без этого обращение к order.client после
        возврата из сервиса (например, в хендлере бота, который хочет
        написать "заказ создан для {order.client.full_name}") упало бы
        с MissingGreenlet — SQLAlchemy не может сделать ленивую
        (lazy) подгрузку связи неявно в асинхронном режиме.
        """
        order = Order(
            client_id=client_id,
            address=address,
            created_by_chat_id=created_by_chat_id,
            carpet_count=carpet_count,
            notes=notes,
            status=OrderStatus.NEW,
        )
        self._session.add(order)
        await self._session.flush()
        await self._session.refresh(order, attribute_names=["client"])
        return order

    async def update_status(self, order_id: int, new_status: OrderStatus) -> Order | None:
        """Обновляет статус заказа. None, если заказ не найден."""
        order = await self._session.get(Order, order_id)
        if order is None:
            return None
        order.status = new_status
        await self._session.flush()
        return order

    async def update_carpet_count(self, order_id: int, carpet_count: int) -> Order | None:
        """Обновляет фактическое количество ковров в заказе."""
        order = await self._session.get(Order, order_id)
        if order is None:
            return None
        order.carpet_count = carpet_count
        await self._session.flush()
        return order
