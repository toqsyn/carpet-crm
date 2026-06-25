from types import SimpleNamespace

import pytest

from carpet_crm.ai import agent
from carpet_crm.db.enums import OrderStatus


class FakeOrderService:
    def __init__(self):
        self.created_orders = []
        self.status_updates = []
        self.carpet_count_updates = []
        self.missing_order_ids = set()

    async def create_order_from_chat(self, data, *, created_by_chat_id):
        self.created_orders.append((data, created_by_chat_id))
        return SimpleNamespace(
            id=10,
            client=SimpleNamespace(full_name=data.client_full_name, phone=data.client_phone),
            address=data.address,
        )

    async def update_status(self, order_id, new_status):
        self.status_updates.append((order_id, new_status))
        if order_id in self.missing_order_ids:
            return None
        return SimpleNamespace(id=order_id, status=new_status)

    async def update_carpet_count(self, order_id, carpet_count):
        self.carpet_count_updates.append((order_id, carpet_count))
        if order_id in self.missing_order_ids:
            return None
        return SimpleNamespace(id=order_id, carpet_count=carpet_count)


def function_call(name, args=None):
    return SimpleNamespace(name=name, args=args or {})


@pytest.mark.parametrize(
    ("call", "expected_update"),
    [
        (
            function_call(
                "update_order_status",
                {"order_id": "12", "new_status": OrderStatus.READY.value},
            ),
            ("status_updates", [(12, OrderStatus.READY)]),
        ),
        (
            function_call("update_carpet_count", {"order_id": "12", "carpet_count": "4"}),
            ("carpet_count_updates", [(12, 4)]),
        ),
    ],
)
async def test_execute_tool_updates_existing_order(call, expected_update):
    service = FakeOrderService()

    result = await agent._execute_tool(call, order_service=service, created_by_chat_id=99)

    attribute, expected_value = expected_update
    assert getattr(service, attribute) == expected_value
    assert result.tool_name == call.name
    assert result.success is True


async def test_execute_tool_creates_order_from_valid_arguments():
    service = FakeOrderService()
    call = function_call(
        "create_order",
        {
            "client_full_name": "Aida Saparova",
            "client_phone": "+77770000000",
            "address": "Abay 10",
            "carpet_count": 2,
        },
    )

    result = await agent._execute_tool(call, order_service=service, created_by_chat_id=99)

    created_data, created_by_chat_id = service.created_orders[0]
    assert created_data.client_full_name == "Aida Saparova"
    assert created_data.carpet_count == 2
    assert created_by_chat_id == 99
    assert result.tool_name == "create_order"
    assert result.success is True


async def test_execute_tool_returns_failure_when_order_is_missing():
    service = FakeOrderService()
    service.missing_order_ids.add(404)

    result = await agent._execute_tool(
        function_call("update_order_status", {"order_id": 404, "new_status": "cancelled"}),
        order_service=service,
        created_by_chat_id=99,
    )

    assert result.tool_name == "update_order_status"
    assert result.success is False


async def test_execute_tool_returns_failure_for_unknown_tool():
    result = await agent._execute_tool(
        function_call("unknown_tool"),
        order_service=FakeOrderService(),
        created_by_chat_id=99,
    )

    assert result.tool_name is None
    assert result.success is False


async def test_process_chat_message_returns_no_access_without_building_client(monkeypatch):
    def fail_if_called():
        raise AssertionError("Gemini client should not be built without allowed tools")

    monkeypatch.setattr(agent, "_build_client", fail_if_called)
    monkeypatch.setattr(agent, "get_settings", lambda: SimpleNamespace(ai_model="test-model"))

    result = await agent.process_chat_message(
        "hello",
        order_service=FakeOrderService(),
        created_by_chat_id=99,
        allowed_tool_names=set(),
    )

    assert result.success is False
    assert result.tool_results == []


async def test_process_chat_message_executes_all_function_calls(monkeypatch):
    response = SimpleNamespace(
        candidates=[
            SimpleNamespace(
                content=SimpleNamespace(
                    parts=[
                        SimpleNamespace(
                            function_call=function_call(
                                "update_order_status",
                                {"order_id": 12, "new_status": "ready"},
                            )
                        ),
                        SimpleNamespace(
                            function_call=function_call(
                                "update_carpet_count",
                                {"order_id": 12, "carpet_count": 4},
                            )
                        ),
                    ]
                )
            )
        ],
        text=None,
    )
    fake_client = SimpleNamespace(
        models=SimpleNamespace(generate_content=lambda **kwargs: response)
    )
    service = FakeOrderService()

    monkeypatch.setattr(agent, "get_settings", lambda: SimpleNamespace(ai_model="test-model"))
    monkeypatch.setattr(agent, "_build_client", lambda: fake_client)
    monkeypatch.setattr(agent, "_to_gemini_tool", lambda tool: tool["name"])
    monkeypatch.setattr(agent.types, "GenerateContentConfig", lambda **kwargs: kwargs)

    result = await agent.process_chat_message(
        "order 12 is ready and has 4 carpets",
        order_service=service,
        created_by_chat_id=99,
        allowed_tool_names={"update_order_status", "update_carpet_count"},
    )

    assert service.status_updates == [(12, OrderStatus.READY)]
    assert service.carpet_count_updates == [(12, 4)]
    assert result.success is True
    assert result.tool_name == "update_order_status"
    assert len(result.tool_results) == 2
