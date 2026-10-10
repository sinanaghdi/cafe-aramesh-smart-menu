from datetime import UTC, datetime
import hashlib
import hmac
import secrets

from fastapi import HTTPException
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import Cafe, Order, OrderCode

ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "draft": {"pending_confirmation", "cancelled", "expired"},
    "pending_confirmation": {"confirmed", "cancelled", "expired"},
    "confirmed": {"preparing", "cancelled"},
    "preparing": {"served", "cancelled"},
    "served": set(),
    "cancelled": set(),
    "expired": set(),
}


def utc_now() -> datetime:
    return datetime.now(UTC)


def as_utc(value: datetime) -> datetime:
    """Normalize timezone-aware and SQLite-returned naive datetimes to UTC."""
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def transition_order(current: str, target: str) -> str:
    allowed = ALLOWED_TRANSITIONS.get(current, set())
    if target not in allowed:
        raise ValueError(f"Illegal order transition: {current} -> {target}")
    return target


def hash_order_code(code: str) -> str:
    secret = settings.order_code_hmac_secret.encode("utf-8")
    return hmac.new(secret, code.encode("ascii"), hashlib.sha256).hexdigest()


def generate_unique_order_code(db: Session, cafe: Cafe) -> tuple[str, str]:
    now = utc_now()
    expired_order_ids = select(OrderCode.order_id).where(
        OrderCode.cafe_id == cafe.id,
        OrderCode.status == "active",
        OrderCode.expires_at <= now,
    )
    db.execute(
        update(Order).where(
            Order.id.in_(expired_order_ids),
            Order.cafe_id == cafe.id,
            Order.status == "pending_confirmation",
        ).values(status="expired")
    )
    db.execute(
        update(OrderCode).where(
            OrderCode.cafe_id == cafe.id,
            OrderCode.status == "active",
            OrderCode.expires_at <= now,
        ).values(status="expired")
    )

    upper_bound = 10 ** settings.order_code_digits
    for _ in range(100):
        code = f"{secrets.randbelow(upper_bound):0{settings.order_code_digits}d}"
        code_hash = hash_order_code(code)
        conflict = db.scalar(
            select(OrderCode.id).where(
                OrderCode.cafe_id == cafe.id,
                OrderCode.code_hash == code_hash,
                OrderCode.status == "active",
                OrderCode.expires_at > now,
            )
        )
        if conflict is None:
            return code, code_hash
    raise HTTPException(status_code=503, detail="تولید کد یکتا ممکن نشد؛ دوباره تلاش کنید")
