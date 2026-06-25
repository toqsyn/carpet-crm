import pytest

from carpet_crm.db.enums import OrderStatus
from carpet_crm.repositories.client_repository import ClientRepository
from carpet_crm.repositories.order_repository import OrderRepository

pytestmark = pytest.mark.integration


async def test_client_repository_creates_and_finds_client_by_phone(db_session):
    repository = ClientRepository(db_session)

    client = await repository.create(
        full_name="Aida Saparova",
        phone="+77770000000",
        address="Abay 10",
    )

    found = await repository.get_by_phone("+77770000000")

    assert found == client
    assert found.id is not None
    assert found.full_name == "Aida Saparova"
    assert found.address == "Abay 10"


async def test_order_repository_creates_lists_and_updates_order(db_session):
    clients = ClientRepository(db_session)
    orders = OrderRepository(db_session)
    client = await clients.create(full_name="Aida Saparova", phone="+77770000000")

    order = await orders.create(
        client_id=client.id,
        address="Abay 10",
        created_by_chat_id=123,
        carpet_count=2,
        notes="Careful with fringe",
    )

    assert order.status == OrderStatus.NEW
    assert order.client.full_name == "Aida Saparova"

    new_orders = await orders.list_by_status(OrderStatus.NEW)
    assert [item.id for item in new_orders] == [order.id]

    await orders.update_status(order.id, OrderStatus.PICKED_UP)
    await orders.update_carpet_count(order.id, 3)
    found = await orders.get_by_id(order.id)

    assert found.status == OrderStatus.PICKED_UP
    assert found.carpet_count == 3
    assert found.client.phone == "+77770000000"


async def test_order_repository_returns_none_for_missing_order(db_session):
    repository = OrderRepository(db_session)

    assert await repository.get_by_id(404) is None
    assert await repository.update_status(404, OrderStatus.CANCELLED) is None
    assert await repository.update_carpet_count(404, 1) is None
