"""Репозиторий для модели Client."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from carpet_crm.db.models import Client


class ClientRepository:
    """Доступ к данным клиентов в базе данных."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, client_id: int) -> Client | None:
        """Возвращает клиента по ID или None, если не найден."""
        return await self._session.get(Client, client_id)

    async def get_by_phone(self, phone: str) -> Client | None:
        """Возвращает клиента по номеру телефона или None."""
        statement = select(Client).where(Client.phone == phone)
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def create(self, *, full_name: str, phone: str, address: str | None = None) -> Client:
        """Создаёт нового клиента (flush, не commit — см. пояснение ниже)."""
        client = Client(full_name=full_name, phone=phone, address=address)
        self._session.add(client)
        await self._session.flush()
        return client
