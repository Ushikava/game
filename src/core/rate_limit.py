import math
import time
from collections import deque
from dataclasses import dataclass

from core.exceptions import TooManyRequestsError
from core.settings import Settings


class RateLimiter:
    def __init__(self, limit: int, window_seconds: float) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self._hits: dict[str, deque[float]] = {}
        self._last_cleanup = time.monotonic()

    def retry_after(self, key: str) -> int | None:
        now = time.monotonic()
        hits = self._fresh_hits(key, now)
        if len(hits) < self.limit:
            return None
        return max(1, math.ceil(hits[0] + self.window_seconds - now))

    def record(self, key: str) -> float:
        now = time.monotonic()
        self._fresh_hits(key, now).append(now)
        return now

    def hit(self, key: str) -> float:
        wait = self.retry_after(key)
        if wait is not None:
            raise TooManyRequestsError(wait)
        return self.record(key)

    def undo(self, key: str, stamp: float) -> None:
        hits = self._hits.get(key)
        if hits is not None and stamp in hits:
            hits.remove(stamp)

    def reset(self, key: str) -> None:
        self._hits.pop(key, None)

    def _fresh_hits(self, key: str, now: float) -> deque[float]:
        self._cleanup(now)
        hits = self._hits.setdefault(key, deque())
        while hits and hits[0] <= now - self.window_seconds:
            hits.popleft()
        return hits

    def _cleanup(self, now: float) -> None:
        if now - self._last_cleanup < self.window_seconds:
            return
        self._last_cleanup = now
        for key, hits in list(self._hits.items()):
            if not hits or hits[-1] <= now - self.window_seconds:
                del self._hits[key]


@dataclass
class Attempt:
    _entries: list[tuple[RateLimiter, str, float]]
    _released: bool = False

    def release(self) -> None:
        if self._released:
            return
        self._released = True
        for limiter, key, stamp in self._entries:
            limiter.undo(key, stamp)


def reserve(*rules: tuple[RateLimiter, str]) -> Attempt:
    waits = [wait for limiter, key in rules if (wait := limiter.retry_after(key)) is not None]
    if waits:
        raise TooManyRequestsError(max(waits))
    return Attempt([(limiter, key, limiter.record(key)) for limiter, key in rules])


@dataclass
class AuthLimits:
    login_per_account_ip: RateLimiter
    login_per_account: RateLimiter
    login_per_ip: RateLimiter
    register_per_ip: RateLimiter
    password_confirm_per_user: RateLimiter

    @classmethod
    def from_settings(cls, config: Settings) -> "AuthLimits":
        return cls(
            login_per_account_ip=RateLimiter(
                config.login_failures_per_account_ip, config.login_failures_per_account_ip_window_seconds
            ),
            login_per_account=RateLimiter(
                config.login_failures_per_account, config.login_failures_per_account_window_seconds
            ),
            login_per_ip=RateLimiter(config.login_failures_per_ip, config.login_failures_per_ip_window_seconds),
            register_per_ip=RateLimiter(config.register_per_ip, config.register_per_ip_window_seconds),
            password_confirm_per_user=RateLimiter(
                config.password_confirm_failures, config.password_confirm_failures_window_seconds
            ),
        )


class TokenBucket:
    def __init__(self, rate_per_second: float, burst: int) -> None:
        self.rate = rate_per_second
        self.capacity = float(burst)
        self._tokens = float(burst)
        self._updated = time.monotonic()

    def take(self) -> bool:
        now = time.monotonic()
        self._tokens = min(self.capacity, self._tokens + (now - self._updated) * self.rate)
        self._updated = now
        if self._tokens < 1:
            return False
        self._tokens -= 1
        return True
