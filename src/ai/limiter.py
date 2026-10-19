"""A tiny per-user rate limit so one person can't use up the shared free AI quota.

It lives in memory, so it resets when the server restarts or wakes up. That is fine
for one small server; a bigger app would keep these counters in Redis.
"""
import time
from collections import defaultdict, deque

from fastapi import HTTPException

MAX_CALLS = 10
WINDOW_SECONDS = 60 * 60   # 10 AI plans per hour per user

_calls: dict[int, deque] = defaultdict(deque)


def check_rate_limit(user_id: int, now: float | None = None) -> None:
    now = time.monotonic() if now is None else now
    calls = _calls[user_id]
    while calls and now - calls[0] >= WINDOW_SECONDS:
        calls.popleft()
    if len(calls) >= MAX_CALLS:
        retry_after = int(WINDOW_SECONDS - (now - calls[0])) + 1
        raise HTTPException(
            status_code=429,
            detail="You've asked Mia for a lot of plans. Please try again a bit later.",
            headers={"Retry-After": str(retry_after)},
        )
    calls.append(now)


def reset() -> None:
    _calls.clear()
