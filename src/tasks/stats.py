from collections import Counter
from datetime import date, datetime, timedelta, timezone


def _to_local_date(moment: datetime, tz_offset_minutes: int) -> date:
    """Turn a stored UTC time into the user's local calendar date.

    tz_offset_minutes is what the browser's `new Date().getTimezoneOffset()` returns:
    UTC minus local time, in minutes. India (UTC+5:30) sends -330.
    """
    if moment.tzinfo is None:               # some databases return naive times; ours are UTC
        moment = moment.replace(tzinfo=timezone.utc)
    moment = moment.astimezone(timezone.utc)
    return (moment - timedelta(minutes=tz_offset_minutes)).date()


def compute_stats(completion_times: list[datetime], tz_offset_minutes: int, now: datetime | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    today = _to_local_date(now, tz_offset_minutes)

    per_day = Counter(_to_local_date(t, tz_offset_minutes) for t in completion_times)

    # Last 7 days, oldest first, ending today
    last_7 = [today - timedelta(days=i) for i in range(6, -1, -1)]
    last_7_days = [{"date": d, "count": per_day.get(d, 0)} for d in last_7]

    # Current streak: count back from today. If nothing is done yet today,
    # start from yesterday so the streak isn't "broken" until the day is over.
    cursor = today if per_day.get(today, 0) > 0 else today - timedelta(days=1)
    current_streak = 0
    while per_day.get(cursor, 0) > 0:
        current_streak += 1
        cursor -= timedelta(days=1)

    # Best streak ever: longest run of consecutive days
    best_streak = 0
    run = 0
    previous = None
    for d in sorted(per_day):
        run = run + 1 if previous and d - previous == timedelta(days=1) else 1
        best_streak = max(best_streak, run)
        previous = d

    return {
        "completed_today": per_day.get(today, 0),
        "completed_last_7_days": sum(item["count"] for item in last_7_days),
        "last_7_days": last_7_days,
        "current_streak": current_streak,
        "best_streak": best_streak,
        "total_completed": len(completion_times),
    }