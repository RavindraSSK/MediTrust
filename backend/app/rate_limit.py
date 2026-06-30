import time
from collections import defaultdict
from threading import Lock


class LoginRateLimiter:
    """
    Simple in-memory sliding-window limiter for failed login attempts.

    Not suitable for multi-process / multi-host deployments (state is per
    process), but it provides basic brute-force protection for a single
    backend instance with no extra infrastructure.
    """

    def __init__(self, max_attempts: int = 5, window_seconds: int = 900):
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._failures: dict[str, list[float]] = defaultdict(list)
        self._lock = Lock()

    def _recent(self, key: str, now: float) -> list[float]:
        attempts = [t for t in self._failures.get(key, []) if now - t < self.window_seconds]
        if attempts:
            self._failures[key] = attempts
        else:
            self._failures.pop(key, None)
        return attempts

    def seconds_until_unblocked(self, key: str) -> int:
        """Return seconds the key must wait, or 0 if it may attempt a login."""
        with self._lock:
            now = time.monotonic()
            attempts = self._recent(key, now)
            if len(attempts) >= self.max_attempts:
                retry_after = int(self.window_seconds - (now - attempts[0])) + 1
                return max(retry_after, 1)
            return 0

    def register_failure(self, key: str) -> None:
        with self._lock:
            now = time.monotonic()
            self._recent(key, now)
            self._failures[key].append(now)

    def reset(self, key: str) -> None:
        with self._lock:
            self._failures.pop(key, None)
