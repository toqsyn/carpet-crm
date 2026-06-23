"""AI-агент: связывает Gemini Function Calling с бизнес-логикой.

Это единственный файл в проекте, который знает про конкретный
SDK провайдера (google-genai). Если в будущем потребуется перейти
на Anthropic или OpenAI, переписывается только этот файл — tools.py
(контракт инструментов), services (бизнес-логика) и всё остальное
не меняются.

Ключевой принцип безопасности: данным, которые вернул LLM, мы не
доверяем напрямую. Любые параметры, извлечённые моделью, проходят
через Pydantic-схему (OrderCreateData) перед тем как попасть в
бизнес-логику — LLM может ошибиться или сгенерировать невалидные
данные, и это не должно дойти до базы данных без проверки.
"""

from dataclasses import dataclass
from typing import Any

from google import genai
from google.genai import types

from carpet_crm.ai.tools import ALL_TOOLS
from carpet_crm.core.config import get_settings
from carpet_crm.db.enums import OrderStatus
from carpet_crm.schemas.order import OrderCreateData
from carpet_crm.services.order_service import OrderService

SYSTEM_PROMPT = """\
Ты — ассистент CRM-системы мойки ковров. Твоя задача — читать
сообщения от сотрудников (операторов, доставки, мойщиков) и вызывать
соответствующий инструмент для управления заказами.

Правила:
- Создавай заказ (create_order) только если в тексте есть явное
  согласие клиента и указаны хотя бы адрес и телефон.
- Никогда не придумывай данные, которых нет в тексте явно.
- Если данных недостаточно для вызова инструмента — не вызывай его,
  и кратко объясни словами, какая информация отсутствует.
"""


@dataclass
class AgentResult:
    """Результат обработки сообщения AI-агентом."""

    reply_text: str
    tool_name: str | None = None
    success: bool = False


def _build_client() -> genai.Client:
    """Создаёт клиент Gemini API с ключом из настроек приложения."""
    settings = get_settings()
    return genai.Client(api_key=settings.gemini_api_key)


def _to_gemini_tool(tool_schema: dict[str, Any]) -> types.Tool:
    """Конвертирует наше нейтральное описание инструмента в формат Gemini SDK."""
    declaration = types.FunctionDeclaration(
        name=tool_schema["name"],
        description=tool_schema["description"],
        parameters=tool_schema["parameters"],
    )
    return types.Tool(function_declarations=[declaration])


async def process_chat_message(
    text: str, *, order_service: OrderService, created_by_chat_id: int
) -> AgentResult:
    """Обрабатывает текст от сотрудника, вызывая нужный инструмент."""
    settings = get_settings()
    client = _build_client()

    gemini_tools = [_to_gemini_tool(tool) for tool in ALL_TOOLS]

    response = client.models.generate_content(
        model=settings.ai_model,
        contents=text,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            tools=gemini_tools,
        ),
    )

    function_call = _extract_function_call(response)
    if function_call is None:
        return AgentResult(reply_text=response.text or "Не удалось обработать сообщение.")

    return await _execute_tool(
        function_call,
        order_service=order_service,
        created_by_chat_id=created_by_chat_id,
    )


def _extract_function_call(response: Any) -> types.FunctionCall | None:
    """Достаёт вызов инструмента из ответа Gemini, если модель его сделала."""
    if not response.candidates:
        return None

    for part in response.candidates[0].content.parts:
        if part.function_call is not None:
            return part.function_call

    return None


async def _execute_tool(
    function_call: types.FunctionCall,
    *,
    order_service: OrderService,
    created_by_chat_id: int,
) -> AgentResult:
    """Выполняет инструмент, который решил вызвать Gemini."""
    name = function_call.name
    args = dict(function_call.args or {})

    if name == "create_order":
        order_data = OrderCreateData.model_validate(args)
        order = await order_service.create_order_from_chat(
            order_data, created_by_chat_id=created_by_chat_id
        )
        return AgentResult(
            reply_text=(
                f"Заказ #{order.id} создан для {order.client.full_name} "
                f"({order.client.phone}), адрес: {order.address}."
            ),
            tool_name=name,
            success=True,
        )

    if name == "update_order_status":
        order_id = int(args["order_id"])
        new_status = OrderStatus(args["new_status"])
        order = await order_service.update_status(order_id, new_status)
        if order is None:
            return AgentResult(
                reply_text=f"Заказ #{order_id} не найден.", tool_name=name, success=False
            )
        return AgentResult(
            reply_text=f"Заказ #{order.id}: статус обновлён на {order.status}.",
            tool_name=name,
            success=True,
        )

    if name == "update_carpet_count":
        order_id = int(args["order_id"])
        carpet_count = int(args["carpet_count"])
        order = await order_service.update_carpet_count(order_id, carpet_count)
        if order is None:
            return AgentResult(
                reply_text=f"Заказ #{order_id} не найден.", tool_name=name, success=False
            )
        return AgentResult(
            reply_text=f"Заказ #{order.id}: количество ковров обновлено на {order.carpet_count}.",
            tool_name=name,
            success=True,
        )

    return AgentResult(
        reply_text=f"Модель вызвала неизвестный инструмент: {name}", success=False
    )
