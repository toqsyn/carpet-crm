"""Точка входа Telegram-бота."""

import asyncio
import logging

from aiogram import Bot, Dispatcher

from carpet_crm.bot.handlers.employee import router as employee_router
from carpet_crm.core.config import get_settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

logger = logging.getLogger(__name__)


async def main() -> None:
    """Создаёт бота, подключает роутеры и запускает polling."""
    settings = get_settings()
    bot = Bot(token=settings.telegram_bot_token)
    dispatcher = Dispatcher()
    dispatcher.include_router(employee_router)

    logger.info("Бот запускается (polling)...")
    await dispatcher.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
