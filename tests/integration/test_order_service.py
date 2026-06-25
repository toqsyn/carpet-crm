import pytest

from carpet_crm.db.enums import OrderStatus
from carpet_crm.repositories.client_repository import ClientRepository
from carpet_crm.schemas.order import OrderCreateData
from carpet_crm.services.order_service import OrderService

pytestmark = pytest.mark.integration


async def test_order_service_creates_order_and_reuses_client_by_phone(db_session):
    service = OrderService(db_session)

    first_order = await service.create_order_from_chat(
        OrderCreateData(
            client_full_name="Aida Saparova",
            client_phone="+77770000000",
            address="Abay 10",
            carpet_count=2,
        ),
        created_by_chat_id=123,
    )
    second_order = await service.create_order_from_chat(
        OrderCreateData(
            client_full_name="Different Name",
            client_phone="+77770000000",
            address="Satpayev 5",
        ),
        created_by_chat_id=456,
    )

    assert first_order.client_id == second_order.client_id
    assert first_order.status == OrderStatus.NEW
    assert second_order.client.full_name == "Aida Saparova"
    assert second_order.address == "Satpayev 5"


async def test_order_service_updates_status_and_carpet_count(db_session):
    client = await ClientRepository(db_session).create(
        full_name="Aida Saparova",
        phone="+77770000000",
    )
    service = OrderService(db_session)
    order = await service.create_order_from_chat(
        OrderCreateData(
            client_full_name=client.full_name,
            client_phone=client.phone,
            address="Abay 10",
        ),
        created_by_chat_id=123,
    )

    updated_status = await service.update_status(order.id, OrderStatus.READY)
    updated_count = await service.update_carpet_count(order.id, 4)

    assert updated_status.status == OrderStatus.READY
    assert updated_count.carpet_count == 4


async def test_order_service_returns_none_for_missing_order(db_session):
    service = OrderService(db_session)

    assert await service.update_status(404, OrderStatus.CANCELLED) is None
    assert await service.update_carpet_count(404, 2) is None
