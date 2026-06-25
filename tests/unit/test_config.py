import pytest

from carpet_crm.core.config import Settings, _parse_chat_ids


def test_parse_chat_ids_trims_spaces_and_ignores_empty_items():
    assert _parse_chat_ids(" 1,2, 3, ,") == {1, 2, 3}


def test_parse_chat_ids_returns_empty_set_for_empty_string():
    assert _parse_chat_ids("") == set()


def test_parse_chat_ids_rejects_non_integer_value():
    with pytest.raises(ValueError):
        _parse_chat_ids("1,not-a-number")


def test_settings_exposes_chat_id_properties_as_sets():
    settings = Settings(
        database_url="postgresql+asyncpg://user:password@localhost:5432/app",
        telegram_bot_token="token",
        gemini_api_key="key",
        telegram_admin_chat_ids="1, 2",
        telegram_operator_chat_ids="3",
        telegram_delivery_chat_ids="4",
        telegram_washer_chat_ids="5",
        telegram_packer_chat_ids="6",
        _env_file=None,
    )

    assert settings.admin_chat_ids == {1, 2}
    assert settings.operator_chat_ids == {3}
    assert settings.delivery_chat_ids == {4}
    assert settings.washer_chat_ids == {5}
    assert settings.packer_chat_ids == {6}
