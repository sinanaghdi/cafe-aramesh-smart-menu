from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import InvalidTokenError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import User
from app.services.auth.tokens import decode_token

_bearer = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(status_code=401, detail="ورود کارکنان لازم است")
    try:
        payload = decode_token(credentials.credentials, expected_type="access")
        user_id = int(payload["sub"])
        cafe_id = int(payload["cafe_id"])
    except (InvalidTokenError, KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=401, detail="توکن نامعتبر یا منقضی است") from exc

    user = db.get(User, user_id)
    if user is None or not user.is_active or user.cafe_id != cafe_id:
        raise HTTPException(status_code=401, detail="کاربر معتبر نیست")
    if payload.get("role") != user.role:
        raise HTTPException(status_code=401, detail="نقش کاربر تغییر کرده است")
    return user


def require_staff(user: User = Depends(get_current_user)) -> User:
    if user.role != "staff":
        raise HTTPException(status_code=403, detail="این بخش فقط برای گارسون است")
    return user


def require_merchant(user: User = Depends(get_current_user)) -> User:
    if user.role != "merchant":
        raise HTTPException(status_code=403, detail="این بخش فقط برای صاحب کافه است")
    return user
