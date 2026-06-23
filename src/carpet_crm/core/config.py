"""Конфигурация приложения.

Все настройки читаются из переменных окружения (файл .env локально,
переменные окружения контейнера в Docker). Использование pydantic-settings
даёт нам валидацию при старте — если забыли указать обязательную
переменную, приложение упадёт сразу при запуске с понятной ошибкой,
а не где-то посреди обработки запроса.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Настройки приложения, загружаемые из переменных окружения."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- База данных ---
    database_url: str
    """Строка подключения к PostgreSQL, например:
    postgresql+asyncpg://user:password@localhost:5432/carpet_crm
    """

    # --- Telegram ---
    telegram_bot_token: str
    """Токен бота, полученный от @BotFather."""

    telegram_operator_chat_id: int | None = None
    """ID чата/группы операторов. Используется для уведомлений.
    Может быть не задан на старте проекта.
    """

    # --- Anthropic AI ---
    anthropic_api_key: str
    """API-ключ Anthropic для работы AI-агента."""

    ai_model: str = "claude-haiku-4-5-20251001"
    """Модель, используемая для извлечения данных заказа и команд.
    Haiku выбран осознанно: задачи структурированные и короткие
    (извлечь поля из текста, вызвать tool), поэтому дорогая модель
    не нужна — это прямо влияет на стоимость эксплуатации проекта.
    """

    # --- Окружение ---
    environment: str = "development"
    """development | production — влияет на уровень логирования и debug-режим."""

    debug: bool = False


@lru_cache
def get_settings() -> Settings:
    """Возвращает закэшированный экземпляр настроек.

    lru_cache гарантирует, что .env читается один раз за всё время
    работы процесса, а не при каждом вызове get_settings().
    """
    return Settings()
