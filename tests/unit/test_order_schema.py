import pytest
from pydantic import ValidationError

from carpet_crm.schemas.order import OrderCreateData


def test_order_create_data_accepts_minimal_valid_payload():
    data = OrderCreateData(
        client_full_name="Aida",
        client_phone="+77770000000",
        address="Abay 10",
    )

    assert data.client_full_name == "Aida"
    assert data.carpet_count is None
    assert data.notes is None


@pytest.mark.parametrize(
    "payload",
    [
        {
            "client_full_name": "",
            "client_phone": "+77770000000",
            "address": "Abay 10",
        },
        {
            "client_full_name": "Aida",
            "client_phone": "1234",
            "address": "Abay 10",
        },
        {
            "client_full_name": "Aida",
            "client_phone": "+77770000000",
            "address": "",
        },
        {
            "client_full_name": "Aida",
            "client_phone": "+77770000000",
            "address": "Abay 10",
            "carpet_count": -1,
        },
    ],
)
def test_order_create_data_rejects_invalid_payload(payload):
    with pytest.raises(ValidationError):
        OrderCreateData.model_validate(payload)
