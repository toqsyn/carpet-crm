"""Обработчик текстовых сообщений от сотрудников.

Это первый и пока единственный хендлер бота: любое текстовое
сообщение от сотрудника передаётся напрямую AI-агенту, который сам
решает, что нужно сделать (создать заказ, сменить статус, и т.д.) —
именно та "свободная" модель общения с ботом, которую обсуждали
на этапе планирования: не жёсткие команды вида /create_order, а
естественный текст.
"""

import logging

from aiogram import Router
from aiogram.types import Message

from carpet_crm.ai.agent import process_chat_message
from carpet_crm.bot.permissions import get_allowed_tool_names, get_employee_role
from carpet_crm.db.session import async_session_factory
from carpet_crm.services.order_service import OrderService

logger = logging.getLogger(__name__)

router = Router(name="employee_messages")


@router.message()
async def handle_employee_message(message: Message) -> None:
    """Обрабатывает любое текстовое сообщение через AI-агента."""
    if message.text is None:
        await message.answer("Я понимаю только текстовые сообщения.")
        return

    role = get_employee_role(message.chat.id)
    allowed_tool_names = get_allowed_tool_names(role)

    async with async_session_factory() as session:
        order_service = OrderService(session)
        try:
            result = await process_chat_message(
                message.text,
                order_service=order_service,
                created_by_chat_id=message.chat.id,
                allowed_tool_names=allowed_tool_names,
            )
        except Exception:
            logger.exception("Не удалось обработать сообщение от сотрудника")
            await message.answer(
                "Не получилось обработать сообщение. Проверьте данные "
                "вручную или попробуйте переформулировать."
            )
            return

    await message.answer(result.reply_text)
