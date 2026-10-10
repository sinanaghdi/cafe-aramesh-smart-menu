from datetime import UTC, datetime, timedelta
import hashlib
import secrets
from typing import Any

import jwt
from jwt import InvalidTokenError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import AuthSession, User
from app.services.orders import as_utc

ISSUER = "cafe-aramesh"


def _now() -> datetime:
    return datetime.now(UTC)


def hash_token_id(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def create_access_token(user: User) -> tuple[str, int]:
    expires_in = settings.jwt_access_minutes * 60
    now = _now()
    payload: dict[str, Any] = {
        "iss": ISSUER,
        "sub": str(user.id),
        "cafe_id": user.cafe_id,
        "role": user.role,
        "typ": "access",
        "iat": now,
        "exp": now + timedelta(seconds=expires_in),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm="HS256"), expires_in


def create_refresh_session(db: Session, user: User) -> str:
    now = _now()
    jti = secrets.token_urlsafe(32)
    expires_at = now + timedelta(days=settings.jwt_refresh_days)
    payload: dict[str, Any] = {
        "iss": ISSUER,
        "sub": str(user.id),
        "cafe_id": user.cafe_id,
        "role": user.role,
        "typ": "refresh",
        "jti": jti,
        "iat": now,
        "exp": expires_at,
    }
    db.add(
        AuthSession(
            cafe_id=user.cafe_id,
            user_id=user.id,
            refresh_jti_hash=hash_token_id(jti),
            expires_at=expires_at,
        )
    )
    return jwt.encode(payload, settings.jwt_secret_key, algorithm="HS256")


def decode_token(token: str, *, expected_type: str) -> dict[str, Any]:
    payload = jwt.decode(
        token,
        settings.jwt_secret_key,
        algorithms=["HS256"],
        issuer=ISSUER,
        options={"require": ["exp", "iat", "iss", "sub", "typ"]},
    )
    if payload.get("typ") != expected_type:
        raise InvalidTokenError("Unexpected token type")
    return payload


def rotate_refresh_session(db: Session, token: str) -> tuple[User, str, str, int]:
    payload = decode_token(token, expected_type="refresh")
    jti = payload.get("jti")
    if not isinstance(jti, str) or not jti:
        raise InvalidTokenError("Missing refresh token identifier")

    record = db.scalar(
        select(AuthSession).where(
            AuthSession.refresh_jti_hash == hash_token_id(jti),
            AuthSession.user_id == int(payload["sub"]),
            AuthSession.cafe_id == int(payload["cafe_id"]),
        ).with_for_update()
    )
    now = _now()
    if record is None or record.revoked_at is not None or as_utc(record.expires_at) <= now:
        raise InvalidTokenError("Refresh session is expired or revoked")

    user = db.get(User, record.user_id)
    if user is None or not user.is_active or user.cafe_id != record.cafe_id:
        raise InvalidTokenError("User is not active")

    record.revoked_at = now
    access_token, expires_in = create_access_token(user)
    refresh_token = create_refresh_session(db, user)
    db.commit()
    return user, access_token, refresh_token, expires_in
