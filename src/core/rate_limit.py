import math
import time
from collections import deque

from core.exceptions import TooManyRequestsError


class RateLimiter:
    def __init__(self, limit: int, window_seconds: float) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self._hits: dict[str, deque[float]] = {}
        self._last_cleanup = time.monotonic()

    def hit(self, key: str) -> None:
        now = time.monotonic()
        self._cleanup(now)
        hits = self._hits.setdefault(key, deque())
        while hits and hits[0] <= now - self.window_seconds:
            hits.popleft()
        if len(hits) >= self.limit:
            raise TooManyRequestsError(math.ceil(hits[0] + self.window_seconds - now))
        hits.append(now)

    def _cleanup(self, now: float) -> None:
        if now - self._last_cleanup < self.window_seconds:
            return
        self._last_cleanup = now
        for key, hits in list(self._hits.items()):
            if not hits or hits[-1] <= now - self.window_seconds:
                del self._hits[key]
