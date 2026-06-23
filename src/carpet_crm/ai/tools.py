"""Описание AI-инструментов (tools) в нейтральном формате.

Здесь описано, ЧТО умеет делать AI-агент — имя инструмента, его
назначение и форма входных параметров через JSON Schema. Этот файл
не знает НИЧЕГО про конкретного провайдера (Gemini/Anthropic/OpenAI) —
JSON Schema — общий стандарт, который с минимальной обёрткой понимают
все три. Когда понадобится сменить провайдера, этот файл не меняется;
переписывается только код вызова API в agent.py.

Реальное выполнение каждого инструмента (вызов OrderService) находится
в agent.py — здесь только контракт "как инструмент выглядит снаружи".
"""

CREATE_ORDER_TOOL = {
    "name": "create_order",
    "description": (
        "Создаёт новый заказ на мойку ковров на основе данных, "
        "извлечённых из переписки оператора с клиентом. Вызывай эту "
        "функцию только после того, как в тексте есть явное согласие "
        "клиента на заказ и указан хотя бы адрес и телефон."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "client_full_name": {
                "type": "string",
                "description": "Полное имя клиента, как указано в переписке.",
            },
            "client_phone": {
                "type": "string",
                "description": (
                    "Номер телефона клиента в любом формате, в котором "
                    "он встретился в чате (нормализация выполняется "
                    "отдельно, не AI-агентом)."
                ),
            },
            "address": {
                "type": "string",
                "description": "Адрес, откуда нужно забрать ковры.",
            },
            "carpet_count": {
                "type": "integer",
                "description": (
                    "Количество ковров, если оно явно упомянуто в "
                    "переписке. Не угадывай и не придумывай число — "
                    "если оно не названо явно, не указывай этот параметр."
                ),
            },
            "notes": {
                "type": "string",
                "description": (
                    "Любые важные детали из переписки: особенности "
                    "ковра, пожелания клиента, договорённости о времени."
                ),
            },
        },
        "required": ["client_full_name", "client_phone", "address"],
    },
}

UPDATE_ORDER_STATUS_TOOL = {
    "name": "update_order_status",
    "description": (
        "Меняет статус существующего заказа по его ID. Используется, "
        "когда доставка или мойщики сообщают о продвижении заказа "
        "по этапам: забрали, в работе, готово, выдано."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "order_id": {
                "type": "integer",
                "description": "ID заказа, который нужно обновить.",
            },
            "new_status": {
                "type": "string",
                "enum": ["picked_up", "in_progress", "ready", "delivered", "cancelled"],
                "description": "Новый статус заказа.",
            },
        },
        "required": ["order_id", "new_status"],
    },
}

UPDATE_CARPET_COUNT_TOOL = {
    "name": "update_carpet_count",
    "description": (
        "Указывает фактическое количество ковров в заказе. Используется "
        "доставкой после физического забора ковров у клиента, когда "
        "точное число становится известно."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "order_id": {
                "type": "integer",
                "description": "ID заказа.",
            },
            "carpet_count": {
                "type": "integer",
                "description": "Фактическое количество ковров.",
            },
        },
        "required": ["order_id", "carpet_count"],
    },
}

ALL_TOOLS = [CREATE_ORDER_TOOL, UPDATE_ORDER_STATUS_TOOL, UPDATE_CARPET_COUNT_TOOL]
