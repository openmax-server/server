import time, logging


class RateLimiter:
    """
    ip rate limiter using sliding window algorithm
    """
    def __init__(self, max_attempts=5, window_seconds=60):
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self.attempts = {}  # {ip: [timestamp, ...]}
        self.logger = logging.getLogger(__name__)

    def is_allowed(self, ip: str) -> bool:
        now = time.monotonic()
        cutoff = now - self.window_seconds

        if ip not in self.attempts:
            self.attempts[ip] = []

        self.attempts[ip] = [t for t in self.attempts[ip] if t > cutoff]

        if len(self.attempts[ip]) >= self.max_attempts:
            self.logger.warning(f"request limit exceeded for {ip}: {len(self.attempts[ip])}/{self.max_attempts}")
            return False

        self.attempts[ip].append(now)
        return True

    def remaining(self, ip: str) -> int:
        now = time.monotonic()
        cutoff = now - self.window_seconds

        entries = self.attempts.get(ip, [])
        active = [t for t in entries if t > cutoff]
        return max(0, self.max_attempts - len(active))

    def retry_after(self, ip: str) -> int:
        entries = self.attempts.get(ip, [])
        if not entries:
            return 0

        now = time.monotonic()
        cutoff = now - self.window_seconds
        active = [t for t in entries if t > cutoff]

        if len(active) < self.max_attempts:
            return 0

        oldest = min(active)
        return max(0, int(oldest + self.window_seconds - now) + 1)
