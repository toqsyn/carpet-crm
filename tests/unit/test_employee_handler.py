import os
from types import SimpleNamespace

os.environ["DATABASE_URL"] = "postgresql+asyncpg://user:password@localhost:5432/app"
os.environ["TELEGRAM_BOT_TOKEN"] = "token"
os.environ["GEMINI_API_KEY"] = "key"
os.environ["DEBUG"] = "false"

from carpet_crm.ai.agent import AgentResult
from carpet_crm.bot.handlers import employee


class FakeMessage:
    def __init__(self, text, chat_id=123):
        self.text = text
        self.chat = SimpleNamespace(id=chat_id)
        self.answers = []

    async def answer(self, text):
        self.answers.append(text)


class FakeSessionContext:
    async def __aenter__(self):
        return SimpleNamespace(name="session")

    async def __aexit__(self, exc_type, exc, traceback):
        return False


async def test_handle_employee_message_replies_to_non_text_message():
    message = FakeMessage(text=None)

    await employee.handle_employee_message(message)

    assert len(message.answers) == 1


async def test_handle_employee_message_passes_role_permissions_to_agent(monkeypatch):
    captured = {}

    async def fake_process_chat_message(
        text,
        *,
        order_service,
        created_by_chat_id,
        allowed_tool_names,
    ):
        captured["text"] = text
        captured["order_service"] = order_service
        captured["created_by_chat_id"] = created_by_chat_id
        captured["allowed_tool_names"] = allowed_tool_names
        return AgentResult(reply_text="done")

    monkeypatch.setattr(employee, "async_session_factory", lambda: FakeSessionContext())
    monkeypatch.setattr(employee, "OrderService", lambda session: SimpleNamespace(session=session))
    monkeypatch.setattr(employee, "get_employee_role", lambda chat_id: "operator")
    monkeypatch.setattr(employee, "get_allowed_tool_names", lambda role: {"create_order"})
    monkeypatch.setattr(employee, "process_chat_message", fake_process_chat_message)

    message = FakeMessage(text="create order", chat_id=123)

    await employee.handle_employee_message(message)

    assert captured["text"] == "create order"
    assert captured["created_by_chat_id"] == 123
    assert captured["allowed_tool_names"] == {"create_order"}
    assert message.answers == ["done"]


async def test_handle_employee_message_sends_error_reply_when_agent_fails(monkeypatch):
    async def fake_process_chat_message(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(employee, "async_session_factory", lambda: FakeSessionContext())
    monkeypatch.setattr(employee, "OrderService", lambda session: SimpleNamespace(session=session))
    monkeypatch.setattr(employee, "get_employee_role", lambda chat_id: "operator")
    monkeypatch.setattr(employee, "get_allowed_tool_names", lambda role: {"create_order"})
    monkeypatch.setattr(employee, "process_chat_message", fake_process_chat_message)

    message = FakeMessage(text="create order", chat_id=123)

    await employee.handle_employee_message(message)

    assert len(message.answers) == 1
    assert message.answers[0] != "done"
