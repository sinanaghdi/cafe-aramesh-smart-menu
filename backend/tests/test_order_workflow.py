from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.models import AuthSession, OrderCode


def _login(client, email="staff@aramesh.local", password="StaffTestPass123!"):
    response = client.post(
        "/v1/auth/login",
        json={"email": email, "password": password, "cafe_slug": "cafe-aramesh"},
    )
    assert response.status_code == 200, response.text
    return response.json()


def _create_order(client, product_id, quantity=2):
    response = client.post(
        "/v1/orders",
        json={
            "table_number": 5,
            "items": [{"product_id": product_id, "quantity": quantity}],
            "total_amount": 1,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_menu_is_loaded_from_database_and_tags_are_returned(api_env):
    client, _, product_id, _ = api_env
    response = client.get("/v1/menu?table=5")
    assert response.status_code == 200
    data = response.json()
    assert data["table_number"] == 5
    product = next(p for p in data["products"] if p["id"] == product_id)
    assert product["name"] == "آمریکانو"
    assert {"key": "temperature", "value": "hot"} in product["tags"]


def test_invalid_table_is_rejected(api_env):
    client, _, _, _ = api_env
    response = client.get("/v1/menu?table=99")
    assert response.status_code == 404


def test_order_total_uses_database_price_and_session_is_required(api_env):
    client, _, product_id, _ = api_env
    order = _create_order(client, product_id, 2)
    assert order["status"] == "pending_confirmation"
    assert order["total_amount"] == 240000
    assert len(order["code"]) == 4
    assert order["code_expires_at"]
    assert order["items"][0]["line_total_amount"] == 240000

    status = client.get(f"/v1/orders/{order['id']}")
    assert status.status_code == 200
    assert status.json()["status"] == "pending_confirmation"

    from app.main import app

    other_client = TestClient(app)
    try:
        response = other_client.get(f"/v1/orders/{order['id']}")
        assert response.status_code == 401
    finally:
        other_client.close()


def test_staff_must_verify_code_and_state_machine_advances(api_env):
    client, _, product_id, _ = api_env
    order = _create_order(client, product_id)
    tokens = _login(client)
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    invalid_transition = client.patch(
        f"/v1/staff/orders/{order['id']}/status",
        headers=headers,
        json={"status": "preparing"},
    )
    assert invalid_transition.status_code == 409

    confirmed = client.post(
        f"/v1/staff/orders/{order['id']}/confirm",
        headers=headers,
        json={"code": order["code"]},
    )
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["status"] == "confirmed"
    assert "total_amount" not in confirmed.json()
    assert "unit_price_amount" not in confirmed.json()["items"][0]

    preparing = client.patch(
        f"/v1/staff/orders/{order['id']}/status",
        headers=headers,
        json={"status": "preparing"},
    )
    assert preparing.status_code == 200
    served = client.patch(
        f"/v1/staff/orders/{order['id']}/status",
        headers=headers,
        json={"status": "served"},
    )
    assert served.status_code == 200
    assert served.json()["status"] == "served"

    replay = client.post(
        f"/v1/staff/orders/{order['id']}/confirm",
        headers=headers,
        json={"code": order["code"]},
    )
    assert replay.status_code == 409


def test_wrong_code_locks_after_attempt_limit(api_env):
    client, _, product_id, _ = api_env
    order = _create_order(client, product_id, 1)
    tokens = _login(client)
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    responses = [
        client.post(
            f"/v1/staff/orders/{order['id']}/confirm",
            headers=headers,
            json={"code": "0000" if order["code"] != "0000" else "1111"},
        )
        for _ in range(5)
    ]
    assert [response.status_code for response in responses][-1] == 429
    locked = client.post(
        f"/v1/staff/orders/{order['id']}/confirm",
        headers=headers,
        json={"code": order["code"]},
    )
    assert locked.status_code == 410


def test_expired_code_expires_the_order(api_env):
    client, SessionFactory, product_id, _ = api_env
    order = _create_order(client, product_id, 1)
    with SessionFactory() as db:
        code_row = db.scalar(select(OrderCode).where(OrderCode.order_id == order["id"]))
        assert code_row is not None
        code_row.expires_at = datetime.now(UTC) - timedelta(minutes=1)
        db.commit()
    tokens = _login(client)
    response = client.post(
        f"/v1/staff/orders/{order['id']}/confirm",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
        json={"code": order["code"]},
    )
    assert response.status_code == 410
    status = client.get(f"/v1/orders/{order['id']}")
    assert status.status_code == 200
    assert status.json()["status"] == "expired"


def test_staff_api_does_not_expose_sales_or_revenue(api_env):
    client, _, product_id, _ = api_env
    _create_order(client, product_id)
    tokens = _login(client)
    response = client.get(
        "/v1/staff/orders",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert response.status_code == 200
    assert len(response.json()) == 1
    record = response.json()[0]
    assert set(record) == {"id", "status", "table_number", "created_at", "notes", "items"}
    assert "total_amount" not in record


def test_merchant_cannot_use_staff_queue(api_env):
    client, _, _, _ = api_env
    tokens = _login(client, "merchant@aramesh.local", "MerchantTestPass123!")
    response = client.get("/v1/staff/orders", headers={"Authorization": f"Bearer {tokens['access_token']}"})
    assert response.status_code == 403


def test_refresh_token_rotates_and_replay_is_rejected(api_env):
    client, SessionFactory, _, _ = api_env
    tokens = _login(client)
    response = client.post("/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert response.status_code == 200, response.text
    rotated = response.json()
    replay = client.post("/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert replay.status_code == 401
    assert rotated["refresh_token"] != tokens["refresh_token"]
    with SessionFactory() as db:
        sessions = db.scalars(select(AuthSession)).all()
        assert len(sessions) == 2
        assert sum(item.revoked_at is not None for item in sessions) == 1


def test_wrong_password_does_not_issue_tokens(api_env):
    client, _, _, _ = api_env
    response = client.post(
        "/v1/auth/login",
        json={"email": "staff@aramesh.local", "password": "wrongpass", "cafe_slug": "cafe-aramesh"},
    )
    assert response.status_code == 401
    assert "access_token" not in response.json()
