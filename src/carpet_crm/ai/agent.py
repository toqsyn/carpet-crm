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

from dataclasses import dataclass, field
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
- Если в одном сообщении упомянуто несколько действий — например,
  одновременно смена статуса заказа и конкретное количество ковров
  ("забрали 3 ковра по заказу 5") — вызови ВСЕ соответствующие
  инструменты за один ответ, а не только один из них.
"""


@dataclass
class ToolExecutionResult:
    """Результат выполнения одного инструмента.

    Раньше агент поддерживал только один вызов функции за раз.
    Gemini физически может вернуть несколько function_call в одном
    ответе (например, на "забрали 3 ковра по заказу 5" — одновременно
    update_order_status и update_carpet_count). Чтобы это можно было
    обработать, каждый отдельный вызов теперь даёт свой собственный
    результат, а AgentResult (см. ниже) объединяет их все.
    """

    reply_text: str
    tool_name: str | None = None
    success: bool = False


@dataclass
class AgentResult:
    """Результат обработки сообщения AI-агентом.

    tool_results может содержать 0 (модель ответила текстом без
    действия), 1 (обычный случай) или несколько элементов (модель
    решила, что нужно выполнить несколько действий сразу).
    reply_text — объединённый текст для показа пользователю, success —
    True только если ВСЕ вызванные инструменты выполнились успешно.
    """

    reply_text: str
    tool_results: list[ToolExecutionResult] = field(default_factory=list)

    @property
    def success(self) -> bool:
        return bool(self.tool_results) and all(r.success for r in self.tool_results)

    @property
    def tool_name(self) -> str | None:
        """Имя первого вызванного инструмента, для обратной совместимости
        с кодом, который интересуется только "что вообще было вызвано".
        """
        return self.tool_results[0].tool_name if self.tool_results else None


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
    text: str,
    *,
    order_service: OrderService,
    created_by_chat_id: int,
    allowed_tool_names: set[str],
) -> AgentResult:
    """Обрабатывает текст от сотрудника, вызывая нужный инструмент(ы).

    Args:
        text: Текст сообщения/переписки, который нужно проанализировать.
        order_service: Сервис, через который реально выполняется
            бизнес-операция после того, как AI решил какой инструмент
            вызвать и с какими параметрами.
        created_by_chat_id: Telegram chat_id сотрудника, отправившего
            сообщение — для аудита, кто инициировал действие.
        allowed_tool_names: Имена инструментов, доступных роли этого
            сотрудника (см. bot/permissions.py). Фильтрация происходит
            до отправки в Gemini: модель не увидит и не сможет
            предложить вызов инструмента, недоступного этой роли, —
            это надёжнее, чем полагаться на проверку постфактум.
    """
    settings = get_settings()
    client = _build_client()

    available_tools = [tool for tool in ALL_TOOLS if tool["name"] in allowed_tool_names]
    if not available_tools:
        return AgentResult(
            reply_text="У вас нет доступа ни к одному действию в этой системе."
        )

    gemini_tools = [_to_gemini_tool(tool) for tool in available_tools]

    response = client.models.generate_content(
        model=settings.ai_model,
        contents=text,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            tools=gemini_tools,
        ),
    )

    function_calls = _extract_function_calls(response)
    if not function_calls:
        return AgentResult(reply_text=response.text or "Не удалось обработать сообщение.")

    tool_results = [
        await _execute_tool(call, order_service=order_service, created_by_chat_id=created_by_chat_id)
        for call in function_calls
    ]

    combined_reply = "\n".join(r.reply_text for r in tool_results)
    return AgentResult(reply_text=combined_reply, tool_results=tool_results)


def _extract_function_calls(response: Any) -> list[types.FunctionCall]:
    """Достаёт ВСЕ вызовы инструментов из ответа Gemini."""
    if not response.candidates:
        return []

    return [
        part.function_call
        for part in response.candidates[0].content.parts
        if part.function_call is not None
    ]


async def _execute_tool(
    function_call: types.FunctionCall,
    *,
    order_service: OrderService,
    created_by_chat_id: int,
) -> ToolExecutionResult:
    """Выполняет инструмент, который решил вызвать Gemini."""
    name = function_call.name
    args = dict(function_call.args or {})

    if name == "create_order":
        order_data = OrderCreateData.model_validate(args)
        order = await order_service.create_order_from_chat(
            order_data, created_by_chat_id=created_by_chat_id
        )
        return ToolExecutionResult(
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
            return ToolExecutionResult(
                reply_text=f"Заказ #{order_id} не найден.", tool_name=name, success=False
            )
        return ToolExecutionResult(
            reply_text=f"Заказ #{order.id}: статус обновлён на {order.status}.",
            tool_name=name,
            success=True,
        )

    if name == "update_carpet_count":
        order_id = int(args["order_id"])
        carpet_count = int(args["carpet_count"])
        order = await order_service.update_carpet_count(order_id, carpet_count)
        if order is None:
            return ToolExecutionResult(
                reply_text=f"Заказ #{order_id} не найден.", tool_name=name, success=False
            )
        return ToolExecutionResult(
            reply_text=f"Заказ #{order.id}: количество ковров обновлено на {order.carpet_count}.",
            tool_name=name,
            success=True,
        )

    return ToolExecutionResult(
        reply_text=f"Модель вызвала неизвестный инструмент: {name}", success=False
    )
