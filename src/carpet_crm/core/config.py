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

    # --- AI-провайдер ---
    ai_provider: str = "gemini"
    """Какой AI-провайдер использовать: gemini | anthropic | openai.
    Сейчас реализован только gemini, но это поле уже здесь, чтобы
    переключение провайдера в будущем было сменой одной переменной
    в .env, а не правкой кода.
    """

    gemini_api_key: str
    """API-ключ Google AI Studio для работы AI-агента."""

    ai_model: str = "gemini-3.1-flash-lite"
    """Модель для извлечения данных заказа и команд из чата.
    Flash выбран осознанно: задачи структурированные и короткие
    (извлечь поля из текста, вызвать tool), к тому же Flash доступен
    на бесплатном уровне Gemini API — что напрямую снижает стоимость
    эксплуатации проекта на этапе разработки и раннего использования.
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
