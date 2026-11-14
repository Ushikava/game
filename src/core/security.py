import asyncio
import hashlib
import secrets
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from fastapi.concurrency import run_in_threadpool
from pwdlib import PasswordHash

from core.exceptions import ServiceUnavailableError, UnauthorizedError
from core.settings import settings

password_hasher = PasswordHash.recommended()
DUMMY_PASSWORD_HASH = password_hasher.hash(secrets.token_urlsafe(16))

_hash_slots = asyncio.Semaphore(settings.password_hash_concurrency)


async def _run_hashing[T](func: Callable[..., T], *args: Any) -> T:
    try:
        async with asyncio.timeout(settings.password_hash_wait_seconds):
            await _hash_slots.acquire()
    except TimeoutError as exc:
        raise ServiceUnavailableError() from exc
    try:
        return await run_in_threadpool(func, *args)
    finally:
        _hash_slots.release()


async def hash_password(password: str) -> str:
    return await _run_hashing(password_hasher.hash, password)


async def verify_password(password: str, password_hash: str) -> tuple[bool, str | None]:
    return await _run_hashing(password_hasher.verify_and_update, password, password_hash)


def create_access_token(user_id: int, token_version: int) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "ver": token_version,
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def decode_access_token(token: str) -> tuple[int, int]:
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm],
            options={"require": ["sub", "ver", "iat", "exp"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise UnauthorizedError("Токен истёк") from exc
    except jwt.InvalidTokenError as exc:
        raise UnauthorizedError("Недействительный токен") from exc

    subject = payload["sub"]
    version = payload["ver"]
    if not isinstance(subject, str) or not subject.isdigit():
        raise UnauthorizedError("Недействительный токен")
    if not isinstance(version, int) or isinstance(version, bool):
        raise UnauthorizedError("Недействительный токен")
    return int(subject), version


def generate_refresh_token() -> str:
    return secrets.token_urlsafe(32)


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def refresh_token_expires_at() -> datetime:
    return datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days)
