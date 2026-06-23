import asyncio
from carpet_crm.db.session import async_session_factory
from carpet_crm.schemas.order import OrderCreateData
from carpet_crm.services.order_service import OrderService
from carpet_crm.repositories.client_repository import ClientRepository


async def test():
    async with async_session_factory() as session:
        service = OrderService(session)
        data = OrderCreateData(
            client_full_name="Айгерим Сериковна",
            client_phone="+77017654321",
            address="Алматы, ул. Абая 10",
            carpet_count=3,
            notes="Большой ковёр, есть пятно от кофе",
        )
        order = await service.create_order_from_chat(data, created_by_chat_id=999)
        print("order:", order.id, order.status, order.client_id)

        clients = ClientRepository(session)
        client = await clients.get_by_id(order.client_id)
        print("client:", client.full_name, client.phone)


asyncio.run(test())