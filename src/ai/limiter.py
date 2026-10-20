"""A tiny per-user rate limit so one person can't use up the shared free AI quota.

It lives in memory, so it resets when the server restarts or wakes up. That is fine
for one small server; a bigger app would keep these counters in Redis.
Each AI feature has its own bucket, so using one doesn't use up the other.
"""
import time
from collections import defaultdict, deque

from fastapi import HTTPException

WINDOW_SECONDS = 60 * 60   # per hour
MAX_CALLS = {"plan": 10, "breakdown": 15}   # calls per user per hour, per feature

_calls: dict[tuple[str, int], deque] = defaultdict(deque)


def check_rate_limit(user_id: int, bucket: str = "plan", now: float | None = None) -> None:
    now = time.monotonic() if now is None else now
    calls = _calls[(bucket, user_id)]
    while calls and now - calls[0] >= WINDOW_SECONDS:
        calls.popleft()
    if len(calls) >= MAX_CALLS[bucket]:
        retry_after = int(WINDOW_SECONDS - (now - calls[0])) + 1
        raise HTTPException(
            status_code=429,
            detail="You've asked Mia for a lot of help. Please try again a bit later.",
            headers={"Retry-After": str(retry_after)},
        )
    calls.append(now)


def reset() -> None:
    _calls.clear()
