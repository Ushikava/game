import datetime
import secrets

import jwt
from fastapi import Request

from core.exceptions import ForbiddenError, UnauthorizedError
from core.settings import ACCESS_TOKEN_EXPIRE_MINUTES, ALGORITHM, SECRET_KEY

REFRESH_TOKEN_EXPIRE_DAYS = 30


def create_access_token(user_id: int, username: str, role: str = "user") -> str:
    expire = datetime.datetime.now(datetime.UTC) + datetime.timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode({"sub": str(user_id), "username": username, "role": role, "exp": expire}, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token() -> tuple[str, datetime.datetime]:
    token = secrets.token_urlsafe(32)
    expires_at = datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    return token, expires_at


def _decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise UnauthorizedError("Токен истёк")
    except (jwt.InvalidTokenError, ValueError, TypeError):
        raise UnauthorizedError("Недействительный токен")


def get_user_from_token(request: Request) -> int:
    token = request.cookies.get("access_token")
    if not token:
        raise UnauthorizedError("Не авторизован")
    payload = _decode_token(token)
    sub = payload.get("sub")
    if not sub:
        raise UnauthorizedError("Недействительный токен")
    return int(sub)


def require_not_observer(request: Request) -> int:
    token = request.cookies.get("access_token")
    if not token:
        raise UnauthorizedError("Не авторизован")
    payload = _decode_token(token)
    if payload.get("role") == "observer":
        raise ForbiddenError("Доступ запрещён")
    sub = payload.get("sub")
    if not sub:
        raise UnauthorizedError("Недействительный токен")
    return int(sub)


def get_optional_user(request: Request) -> int | None:
    token = request.cookies.get("access_token")
    if not token:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        sub = payload.get("sub")
        if not sub:
            return None
        return int(sub)
    except Exception:
        return None