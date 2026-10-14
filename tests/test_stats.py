"""Streaks and weekly numbers.

The first half tests the maths directly with fixed dates, so the results never
depend on what day you run the tests. The second half tests the real API route.
"""
from datetime import datetime, timezone

from src.tasks.stats import compute_stats

IST = -330  # what the browser sends for India (UTC+5:30)


def at(year, month, day, hour=12, minute=0):
    return datetime(year, month, day, hour, minute, tzinfo=timezone.utc)


NOW = at(2026, 10, 12, 10, 30)  # 16:00 on 12 Oct in India


# ---------- the maths ----------
def test_no_completed_tasks_means_no_streak():
    stats = compute_stats([], IST, NOW)

    assert stats["current_streak"] == 0
    assert stats["best_streak"] == 0
    assert stats["completed_today"] == 0
    assert len(stats["last_7_days"]) == 7
    assert stats["last_7_days"][-1]["date"].isoformat() == "2026-10-12"  # the list ends with today


def test_streak_counts_consecutive_days_up_to_today():
    times = [at(2026, 10, 12, 5), at(2026, 10, 11, 5), at(2026, 10, 10, 5), at(2026, 10, 8, 5)]
    stats = compute_stats(times, IST, NOW)

    assert stats["current_streak"] == 3  # 12, 11, 10 (the 9th is missing)
    assert stats["completed_today"] == 1


def test_streak_survives_until_the_day_is_over():
    times = [at(2026, 10, 11, 5), at(2026, 10, 10, 5)]  # nothing done yet today
    assert compute_stats(times, IST, NOW)["current_streak"] == 2


def test_streak_breaks_after_a_fully_missed_day():
    times = [at(2026, 10, 10, 5), at(2026, 10, 9, 5)]  # nothing yesterday or today
    assert compute_stats(times, IST, NOW)["current_streak"] == 0


def test_best_streak_can_be_older_than_the_current_one():
    times = [at(2026, 9, 1 + i, 5) for i in range(5)] + [at(2026, 10, 12, 5)]
    stats = compute_stats(times, IST, NOW)

    assert stats["best_streak"] == 5
    assert stats["current_streak"] == 1


def test_many_tasks_on_one_day_count_as_one_streak_day():
    times = [at(2026, 10, 12, hour) for hour in (3, 4, 5, 6)]
    stats = compute_stats(times, IST, NOW)

    assert stats["completed_today"] == 4
    assert stats["current_streak"] == 1


def test_days_follow_the_users_timezone():
    # 20:00 UTC on 11 Oct is 01:30 on 12 Oct in India, so it is "today" for an Indian user...
    late_evening_utc = [at(2026, 10, 11, 20, 0)]
    assert compute_stats(late_evening_utc, IST, NOW)["completed_today"] == 1
    # ...but it was still yesterday for someone in UTC.
    assert compute_stats(late_evening_utc, 0, NOW)["completed_today"] == 0


def test_week_window_and_totals():
    times = [at(2026, 10, 12, 5), at(2026, 10, 6, 5), at(2026, 10, 5, 5)]  # the 5th is outside the 7 days
    stats = compute_stats(times, IST, NOW)

    assert stats["completed_last_7_days"] == 2
    assert stats["total_completed"] == 3


def test_times_without_a_timezone_are_treated_as_utc():
    stats = compute_stats([datetime(2026, 10, 12, 5, 0)], IST, NOW)
    assert stats["completed_today"] == 1


# ---------- the API route ----------
def test_stats_route_counts_what_i_completed(client, create_task, alice):
    for title in ("a", "b", "c"):
        create_task(alice, title=title, completed=True)
    create_task(alice, title="still pending")

    response = client.get("/tasks/stats?tz_offset=-330", headers=alice)

    assert response.status_code == 200
    stats = response.json()
    assert stats["completed_today"] == 3
    assert stats["current_streak"] == 1
    assert stats["total_completed"] == 3
    assert len(stats["last_7_days"]) == 7
    assert stats["last_7_days"][-1]["count"] == 3


def test_stats_are_private_to_each_user(client, create_task, alice, bob):
    create_task(alice, completed=True)

    assert client.get("/tasks/stats", headers=bob).json()["total_completed"] == 0


def test_stats_route_requires_login(client):
    assert client.get("/tasks/stats").status_code == 401


def test_stats_route_rejects_a_nonsense_timezone(client, alice):
    assert client.get("/tasks/stats?tz_offset=99999", headers=alice).status_code == 422
