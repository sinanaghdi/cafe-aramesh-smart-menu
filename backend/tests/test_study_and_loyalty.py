from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.models import (
    ClubSession, LoyaltyAccount, LoyaltyRedemption, LoyaltyRule, Order, OtpVerification,
    Reward, StudyModeRule, StudySession, User,
)


def _login(client, email="staff@aramesh.local", password="StaffTestPass123!"):
    response = client.post("/v1/auth/login", json={
        "email": email, "password": password, "cafe_slug": "cafe-aramesh",
    })
    assert response.status_code == 200, response.text
    return response.json()


def _create_order(client, product_id, *, study=False, duration=120, quantity=1):
    return client.post("/v1/orders", json={
        "table_number": 5,
        "items": [{"product_id": product_id, "quantity": quantity}],
        "study_mode_requested": study,
        "study_duration_minutes": duration if study else None,
    })


def _enroll(client, phone="09123456789"):
    request = client.post("/v1/club/otp/request", json={"phone": phone, "consent": True})
    assert request.status_code == 200, request.text
    code = request.json()["debug_code"]
    assert code and len(code) == 6
    result = client.post("/v1/club/otp/verify", json={"phone": phone, "code": code})
    assert result.status_code == 200, result.text
    return result.json()


def test_study_voucher_is_issued_only_after_staff_confirmation_and_extends(api_env):
    client, _, product_id, _ = api_env
    created = _create_order(client, product_id, study=True, duration=120)
    assert created.status_code == 201, created.text
    order1 = created.json()
    pending = client.get(f"/v1/orders/{order1['id']}").json()["study_session"]
    assert pending["status"] == "pending"
    assert pending["wifi_code"] is None

    staff = _login(client)
    headers = {"Authorization": f"Bearer {staff['access_token']}"}
    confirmed = client.post(
        f"/v1/staff/orders/{order1['id']}/confirm", headers=headers,
        json={"code": order1["code"]},
    )
    assert confirmed.status_code == 200, confirmed.text
    session1 = client.get(f"/v1/orders/{order1['id']}").json()["study_session"]
    assert session1["status"] == "active"
    assert session1["wifi_code"].startswith("AR-")
    expiry1 = datetime.fromisoformat(session1["expires_at"].replace("Z", "+00:00"))

    created2 = _create_order(client, product_id, study=True, duration=120)
    assert created2.status_code == 201, created2.text
    order2 = created2.json()
    confirmed2 = client.post(
        f"/v1/staff/orders/{order2['id']}/confirm", headers=headers,
        json={"code": order2["code"]},
    )
    assert confirmed2.status_code == 200, confirmed2.text
    session2 = client.get(f"/v1/orders/{order2['id']}").json()["study_session"]
    expiry2 = datetime.fromisoformat(session2["expires_at"].replace("Z", "+00:00"))
    assert session2["status"] == "active"
    assert session2["id"] == session1["id"]
    assert session2["wifi_code"].startswith("AR-")
    assert expiry2 >= expiry1 + timedelta(minutes=119)


def test_study_rules_enforce_minimum_purchase_duration_and_merchant_role(api_env):
    client, SessionFactory, product_id, cafe_id = api_env
    with SessionFactory() as db:
        rule = db.scalar(select(StudyModeRule).where(StudyModeRule.cafe_id == cafe_id))
        assert rule is not None
        rule.minimum_order_amount = 200000
        db.commit()
    too_small = _create_order(client, product_id, study=True, quantity=1)
    assert too_small.status_code == 422
    wrong_duration = _create_order(client, product_id, study=True, duration=240, quantity=2)
    assert wrong_duration.status_code == 422

    merchant = _login(client, "merchant@aramesh.local", "MerchantTestPass123!")
    headers = {"Authorization": f"Bearer {merchant['access_token']}"}
    get_rules = client.get("/v1/merchant/study-rules", headers=headers)
    assert get_rules.status_code == 200
    updated = client.put(
        "/v1/merchant/study-rules", headers=headers,
        json={**get_rules.json(), "minimum_order_amount": 0, "allowed_durations_minutes": [120, 180, 240]},
    )
    assert updated.status_code == 200, updated.text
    allowed = _create_order(client, product_id, study=True, duration=240)
    assert allowed.status_code == 201, allowed.text

    staff = _login(client)
    denied = client.get("/v1/merchant/loyalty-rules", headers={"Authorization": f"Bearer {staff['access_token']}"})
    assert denied.status_code == 403


def test_otp_requires_consent_and_points_are_awarded_once_on_confirmation(api_env):
    client, SessionFactory, product_id, _ = api_env
    no_consent = client.post("/v1/club/otp/request", json={"phone": "09123456789", "consent": False})
    assert no_consent.status_code == 422

    account = _enroll(client)
    assert account["points_balance"] == 0
    response = _create_order(client, product_id)
    assert response.status_code == 201, response.text
    order = response.json()
    with SessionFactory() as db:
        stored = db.get(Order, order["id"])
        assert stored is not None
        member = db.scalar(select(User).where(User.phone == "+989123456789"))
        assert member is not None
        assert stored.loyalty_user_id == member.id

    staff = _login(client)
    headers = {"Authorization": f"Bearer {staff['access_token']}"}
    confirm = client.post(f"/v1/staff/orders/{order['id']}/confirm", headers=headers, json={"code": order["code"]})
    assert confirm.status_code == 200
    after = client.get("/v1/club/account")
    assert after.status_code == 200
    assert after.json()["points_balance"] == 10
    repeat = client.post(f"/v1/staff/orders/{order['id']}/confirm", headers=headers, json={"code": order["code"]})
    assert repeat.status_code == 409
    assert client.get("/v1/club/account").json()["points_balance"] == 10


def test_otp_is_single_use_and_wrong_attempts_lock_challenge(api_env):
    client, SessionFactory, _, cafe_id = api_env
    request = client.post("/v1/club/otp/request", json={"phone": "09120000001", "consent": True})
    assert request.status_code == 200, request.text
    code = request.json()["debug_code"]
    wrong = "000000" if code != "000000" else "000001"
    for index in range(5):
        result = client.post("/v1/club/otp/verify", json={"phone": "09120000001", "code": wrong})
        assert result.status_code == (429 if index == 4 else 400)

    request2 = client.post("/v1/club/otp/request", json={"phone": "09120000002", "consent": True})
    assert request2.status_code == 200
    code2 = request2.json()["debug_code"]
    with SessionFactory() as db:
        challenge = db.scalar(select(OtpVerification).where(
            OtpVerification.cafe_id == cafe_id,
            OtpVerification.phone_e164 == "+989120000002",
        ))
        assert challenge is not None
        challenge.expires_at = datetime.now(UTC) - timedelta(minutes=1)
        db.commit()
    expired = client.post("/v1/club/otp/verify", json={"phone": "09120000002", "code": code2})
    assert expired.status_code == 410


def test_reward_redemption_is_idempotent_and_account_deletion_erases_personal_data(api_env):
    client, SessionFactory, _, cafe_id = api_env
    _enroll(client, "09123456780")
    with SessionFactory() as db:
        user = db.scalar(select(User).where(User.phone == "+989123456780"))
        assert user is not None
        account = db.scalar(select(LoyaltyAccount).where(LoyaltyAccount.user_id == user.id))
        assert account is not None
        account.points_balance = 10
        db.commit()
        reward = db.scalar(select(Reward).where(Reward.cafe_id == cafe_id))
        assert reward is not None
        reward_id = reward.id
        user_id = user.id

    payload = {"idempotency_key": "redeem-test-once-0001"}
    first = client.post(f"/v1/club/rewards/{reward_id}/redeem", json=payload)
    assert first.status_code == 200, first.text
    second = client.post(f"/v1/club/rewards/{reward_id}/redeem", json=payload)
    assert second.status_code == 200, second.text
    assert first.json()["redemption_id"] == second.json()["redemption_id"]
    assert first.json()["remaining_points"] == 5
    assert second.json()["remaining_points"] == 5

    deleted = client.post("/v1/club/account/delete")
    assert deleted.status_code == 204
    assert client.get("/v1/club/account").status_code == 401
    with SessionFactory() as db:
        user = db.get(User, user_id)
        assert user is not None and user.phone is None and user.email is None
        assert user.consent_at is None and not user.is_active
        assert db.scalars(select(ClubSession).where(ClubSession.user_id == user_id)).all() == []
        assert db.scalars(select(LoyaltyRedemption).all()).all() == []
