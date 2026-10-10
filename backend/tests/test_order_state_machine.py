import pytest

from app.services.orders import ALLOWED_TRANSITIONS, transition_order


def test_happy_path_order_transitions():
    status = "draft"
    for next_status in ("pending_confirmation", "confirmed", "preparing", "served"):
        status = transition_order(status, next_status)
    assert status == "served"


@pytest.mark.parametrize(
    ("current", "target"),
    [
        ("pending_confirmation", "preparing"),
        ("draft", "served"),
        ("served", "preparing"),
        ("cancelled", "confirmed"),
        ("expired", "confirmed"),
        ("confirmed", "confirmed"),
        ("preparing", "confirmed"),
    ],
)
def test_illegal_order_transitions_are_rejected(current, target):
    with pytest.raises(ValueError, match="Illegal order transition"):
        transition_order(current, target)


def test_cancel_and_expire_are_terminal():
    assert transition_order("pending_confirmation", "cancelled") == "cancelled"
    assert transition_order("pending_confirmation", "expired") == "expired"
    assert ALLOWED_TRANSITIONS["cancelled"] == set()
    assert ALLOWED_TRANSITIONS["expired"] == set()
