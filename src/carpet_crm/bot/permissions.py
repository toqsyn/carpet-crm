"""Роли сотрудников и их права на использование AI-инструментов.

Жёсткое ограничение на уровне кода (а не "мягкая" просьба к LLM
учитывать роль) — намеренное решение: данным и решениям LLM мы не
доверяем напрямую (см. agent.py), и доступ к бизнес-операциям не
исключение. Доставка физически не должна иметь возможности вызвать
create_order, даже если случайно сформулирует просьбу похожим образом —
вызов отфильтровывается до того, как дойдёт до Gemini.
"""

from enum import StrEnum

from carpet_crm.ai.tools import ALL_TOOLS
from carpet_crm.core.config import get_settings


class EmployeeRole(StrEnum):
    """Роль сотрудника, определяющая какие действия ему доступны."""

    ADMIN = "admin"
    """Полный доступ ко всем инструментам — владелец/администратор
    системы. Используется для тестирования и ручного управления,
    когда роль конкретного действия неважна.
    """

    OPERATOR = "operator"
    """Принимает заказы от клиентов в WhatsApp, создаёт их в системе."""

    DELIVERY = "delivery"
    """Забирает и привозит ковры, фиксирует фактическое количество."""

    WASHER = "washer"
    """Моет ковры, переводит заказ в статус in_progress."""

    PACKER = "packer"
    """Упаковывает ковры после сушки, завершает заказ статусом ready.

    Отдельного статуса PACKAGING пока нет (см. config.py) — это
    сознательное упрощение MVP. Упаковщик использует тот же
    update_order_status, что и мойщик, просто с другим значением
    статуса; права это не путает, так как оба используют один
    инструмент по разным, явно описанным причинам.
    """

    UNKNOWN = "unknown"
    """Сотрудник не найден ни в одном списке ролей в .env."""


ROLE_ALLOWED_TOOLS: dict[EmployeeRole, set[str]] = {
    EmployeeRole.ADMIN: {tool["name"] for tool in ALL_TOOLS},
    EmployeeRole.OPERATOR: {"create_order"},
    EmployeeRole.DELIVERY: {"update_order_status", "update_carpet_count"},
    EmployeeRole.WASHER: {"update_order_status"},
    EmployeeRole.PACKER: {"update_order_status"},
    EmployeeRole.UNKNOWN: set(),
}
"""Какие инструменты (по имени из tools.py) доступны каждой роли.

ADMIN собирается динамически из ALL_TOOLS, а не захардкожен явным
списком имён — это гарантирует, что при добавлении нового инструмента
в tools.py администратор автоматически получает к нему доступ, без
риска забыть обновить список вручную в этом файле.
"""


def get_employee_role(chat_id: int) -> EmployeeRole:
    """Определяет роль сотрудника по его Telegram chat_id.

    Если один и тот же chat_id окажется сразу в нескольких списках
    ролей в .env (ошибка конфигурации) — возвращается первая найденная
    по порядку проверки роль. Это не валидируется отдельно, потому что
    для текущего маленького размера команды конфигурация полностью
    видна и проверяется глазами при правке .env.
    """
    settings = get_settings()

    if chat_id in settings.admin_chat_ids:
        return EmployeeRole.ADMIN
    if chat_id in settings.operator_chat_ids:
        return EmployeeRole.OPERATOR
    if chat_id in settings.delivery_chat_ids:
        return EmployeeRole.DELIVERY
    if chat_id in settings.washer_chat_ids:
        return EmployeeRole.WASHER
    if chat_id in settings.packer_chat_ids:
        return EmployeeRole.PACKER

    return EmployeeRole.UNKNOWN


def get_allowed_tool_names(role: EmployeeRole) -> set[str]:
    """Возвращает имена инструментов, доступных указанной роли."""
    return ROLE_ALLOWED_TOOLS[role]
