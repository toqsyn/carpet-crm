from types import SimpleNamespace

import pytest

from carpet_crm.ai.tools import ALL_TOOLS
from carpet_crm.bot import permissions
from carpet_crm.bot.permissions import EmployeeRole, get_allowed_tool_names, get_employee_role


@pytest.fixture
def fake_settings(monkeypatch):
    settings = SimpleNamespace(
        admin_chat_ids={1},
        operator_chat_ids={2},
        delivery_chat_ids={3},
        washer_chat_ids={4},
        packer_chat_ids={5},
    )
    monkeypatch.setattr(permissions, "get_settings", lambda: settings)
    return settings


@pytest.mark.parametrize(
    ("chat_id", "expected_role"),
    [
        (1, EmployeeRole.ADMIN),
        (2, EmployeeRole.OPERATOR),
        (3, EmployeeRole.DELIVERY),
        (4, EmployeeRole.WASHER),
        (5, EmployeeRole.PACKER),
        (999, EmployeeRole.UNKNOWN),
    ],
)
def test_get_employee_role_returns_role_for_configured_chat_id(
    fake_settings, chat_id, expected_role
):
    assert get_employee_role(chat_id) == expected_role


def test_get_employee_role_uses_first_matching_role_when_chat_id_is_duplicated(
    fake_settings,
):
    fake_settings.operator_chat_ids.add(1)

    assert get_employee_role(1) == EmployeeRole.ADMIN


@pytest.mark.parametrize(
    ("role", "expected_tool_names"),
    [
        (EmployeeRole.OPERATOR, {"create_order"}),
        (EmployeeRole.DELIVERY, {"update_order_status", "update_carpet_count"}),
        (EmployeeRole.WASHER, {"update_order_status"}),
        (EmployeeRole.PACKER, {"update_order_status"}),
        (EmployeeRole.UNKNOWN, set()),
    ],
)
def test_get_allowed_tool_names_returns_tools_for_role(role, expected_tool_names):
    assert get_allowed_tool_names(role) == expected_tool_names


def test_admin_is_allowed_to_use_every_registered_tool():
    expected_tool_names = {tool["name"] for tool in ALL_TOOLS}

    assert get_allowed_tool_names(EmployeeRole.ADMIN) == expected_tool_names
