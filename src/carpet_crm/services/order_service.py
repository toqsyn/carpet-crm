"""Бизнес-логика, связанная с заказами."""

from sqlalchemy.ext.asyncio import AsyncSession

from carpet_crm.db.enums import OrderStatus
from carpet_crm.db.models import Order
from carpet_crm.repositories.client_repository import ClientRepository
from carpet_crm.repositories.order_repository import OrderRepository
from carpet_crm.schemas.order import OrderCreateData


class OrderService:
    """Бизнес-операции над заказами."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._clients = ClientRepository(session)
        self._orders = OrderRepository(session)

    async def create_order_from_chat(
        self, data: OrderCreateData, *, created_by_chat_id: int
    ) -> Order:
        """Создаёт заказ из данных, извлечённых AI-агентом из переписки.

        Бизнес-правило: клиент идентифицируется по номеру телефона.
        Если уже обращался раньше — заказ привязывается к существующему
        клиенту, а не создаётся дубликат.
        """
        client = await self._clients.get_by_phone(data.client_phone)
        if client is None:
            client = await self._clients.create(
                full_name=data.client_full_name,
                phone=data.client_phone,
            )

        order = await self._orders.create(
            client_id=client.id,
            address=data.address,
            created_by_chat_id=created_by_chat_id,
            carpet_count=data.carpet_count,
            notes=data.notes,
        )

        await self._session.commit()
        return order

    async def update_status(self, order_id: int, new_status: OrderStatus) -> Order | None:
        """Меняет статус заказа."""
        order = await self._orders.update_status(order_id, new_status)
        if order is None:
            return None
        await self._session.commit()
        return order

    async def update_carpet_count(self, order_id: int, carpet_count: int) -> Order | None:
        """Указывает фактическое количество ковров."""
        order = await self._orders.update_carpet_count(order_id, carpet_count)
        if order is None:
            return None
        await self._session.commit()
        return order
