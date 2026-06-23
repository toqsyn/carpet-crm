"""Конфигурация приложения.

Все настройки читаются из переменных окружения (файл .env локально,
переменные окружения контейнера в Docker). Использование pydantic-settings
даёт нам валидацию при старте — если забыли указать обязательную
переменную, приложение упадёт сразу при запуске с понятной ошибкой,
а не где-то посреди обработки запроса.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


def _parse_chat_ids(raw: str) -> set[int]:
    """Парсит строку вида "111, 222,333" в {111, 222, 333}.

    Пустые элементы (например, из-за лишней запятой или пустой строки
    целиком) пропускаются, а не вызывают ошибку — конфигурация ролей
    не должна "падать" из-за опечатки с лишним пробелом или запятой.
    """
    return {int(chat_id.strip()) for chat_id in raw.split(",") if chat_id.strip()}


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

    # --- Telegram: роли сотрудников ---
    telegram_admin_chat_ids: str = ""
    """Список chat_id администраторов через запятую.
    Полный доступ ко всем инструментам — используется владельцем
    бизнеса/разработчиком для тестирования и ручного управления.
    """

    telegram_operator_chat_ids: str = ""
    """Список chat_id операторов через запятую, например: "111,222".
    Операторы могут создавать заказы (create_order).
    """

    telegram_delivery_chat_ids: str = ""
    """Список chat_id сотрудников доставки через запятую.
    Доставка может менять статус и указывать количество ковров.
    """

    telegram_washer_chat_ids: str = ""
    """Список chat_id мойщиков через запятую.
    Мойщики могут переводить заказ в статус in_progress.
    """

    telegram_packer_chat_ids: str = ""
    """Список chat_id упаковщиков через запятую.
    Упаковщик завершает заказ после сушки и упаковки, выставляя
    статус READY. Отдельного статуса PACKAGING пока нет — это
    сознательное упрощение MVP (см. permissions.py); реальный
    процесс шире: доставка забирает -> мойщик моет -> упаковщик
    упаковывает после сушки -> доставка везёт обратно. Когда дойдём
    до пересмотра бизнес-процесса целиком, появится отдельный статус.
    """
    @property
    def admin_chat_ids(self) -> set[int]:
        return _parse_chat_ids(self.telegram_admin_chat_ids)

    @property
    def operator_chat_ids(self) -> set[int]:
        """Распарсенный набор chat_id операторов.

        Хранится в .env как простая строка через запятую (легко
        редактировать руками), но остальному коду удобнее работать
        с set[int] для быстрой проверки "содержится ли" и без риска
        дублирования значений.
        """
        return _parse_chat_ids(self.telegram_operator_chat_ids)

    @property
    def delivery_chat_ids(self) -> set[int]:
        return _parse_chat_ids(self.telegram_delivery_chat_ids)

    @property
    def washer_chat_ids(self) -> set[int]:
        return _parse_chat_ids(self.telegram_washer_chat_ids)

    @property
    def packer_chat_ids(self) -> set[int]:
        return _parse_chat_ids(self.telegram_packer_chat_ids)

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
