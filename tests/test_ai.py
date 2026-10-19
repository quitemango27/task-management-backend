"""Tests for the AI daily plan.

The real Groq model is NEVER called here (it would be slow, cost quota, and give
different answers each time). We swap it for a fake that returns a fixed answer,
but the real prompt and the real cleanup code still run.
"""
from datetime import date, timedelta
from types import SimpleNamespace

import pytest
from langchain_core.runnables import RunnableLambda

from main import app
from src.ai import limiter, planner
from src.ai.dtos import AIPlan, PlanPick
from src.ai.router import get_plan_model


def fake_model(picks, summary="You've got this!", seen=None):
    """A stand-in for Groq. Optionally records the prompt it was given."""

    def respond(prompt_value):
        if seen is not None:
            seen.append(prompt_value.to_string())
        return AIPlan(summary=summary, picks=picks)

    return RunnableLambda(respond)


@pytest.fixture(autouse=True)
def clean_state():
    limiter.reset()
    yield
    app.dependency_overrides.pop(get_plan_model, None)
    limiter.reset()


def use_model(model):
    app.dependency_overrides[get_plan_model] = lambda: model


def task(id, title="T", priority="medium", due=None):
    return SimpleNamespace(id=id, title=title, priority=priority, due_date=due)


TODAY = date(2026, 10, 16)


# ---------- the planner on its own ----------

def test_no_pending_tasks_skips_the_ai():
    def boom(_):
        raise AssertionError("AI should not be called when there is nothing to plan")

    plan = planner.generate_daily_plan([], TODAY, RunnableLambda(boom))
    assert plan.items == []
    assert plan.summary


def test_prompt_contains_task_facts_but_not_descriptions():
    seen = []
    tasks = [task(1, "Pay rent", "high", TODAY - timedelta(days=2)), task(2, "Read book", "low", None)]
    planner.generate_daily_plan(tasks, TODAY, fake_model([PlanPick(task_id=1, reason="Overdue")], seen=seen))
    text = seen[0]
    assert "Today is 2026-10-16" in text
    assert 'id=1 | "Pay rent" | priority=high' in text
    assert "OVERDUE by 2 days" in text
    assert "no due date" in text


def test_ai_cannot_invent_or_repeat_tasks():
    tasks = [task(1, "Real task")]
    picks = [PlanPick(task_id=999, reason="Made up"), PlanPick(task_id=1, reason="Good"), PlanPick(task_id=1, reason="Again")]
    plan = planner.generate_daily_plan(tasks, TODAY, fake_model(picks))
    assert [i.task_id for i in plan.items] == [1]
    assert plan.items[0].title == "Real task"          # title comes from OUR data, not the AI


def test_plan_is_capped_at_five_items():
    tasks = [task(i) for i in range(1, 9)]
    picks = [PlanPick(task_id=i, reason="ok") for i in range(1, 9)]
    plan = planner.generate_daily_plan(tasks, TODAY, fake_model(picks))
    assert len(plan.items) == 5


def test_only_30_tasks_are_sent_most_urgent_first():
    seen = []
    tasks = [task(i, f"T{i}", due=TODAY + timedelta(days=i)) for i in range(1, 41)]
    planner.generate_daily_plan(tasks, TODAY, fake_model([], seen=seen))
    assert seen[0].count("id=") == 30
    assert "id=1 |" in seen[0] and "id=40 |" not in seen[0]


# ---------- the API endpoint ----------

def test_daily_plan_requires_login(client):
    use_model(fake_model([]))
    assert client.post("/ai/daily-plan").status_code == 401


def test_daily_plan_end_to_end(client, alice, create_task):
    t1 = create_task(alice, title="Submit report", priority="high").json()
    create_task(alice, title="Already done", completed=True)
    use_model(fake_model([PlanPick(task_id=t1["id"], reason="It is due soon")], summary="Big day ahead!"))

    res = client.post("/ai/daily-plan", headers=alice)
    assert res.status_code == 200
    body = res.json()
    assert body["summary"] == "Big day ahead!"
    assert body["items"] == [
        {"task_id": t1["id"], "title": "Submit report", "priority": "high", "due_date": None, "reason": "It is due soon"}
    ]


def test_only_the_users_own_pending_tasks_reach_the_ai(client, alice, bob, create_task):
    create_task(alice, title="Alice pending")
    create_task(alice, title="Alice done", completed=True)
    create_task(bob, title="Bob secret")
    seen = []
    use_model(fake_model([], seen=seen))

    client.post("/ai/daily-plan", headers=alice)
    assert "Alice pending" in seen[0]
    assert "Alice done" not in seen[0]
    assert "Bob secret" not in seen[0]


def test_no_tasks_returns_friendly_empty_plan(client, alice):
    use_model(fake_model([]))
    res = client.post("/ai/daily-plan", headers=alice)
    assert res.status_code == 200
    assert res.json()["items"] == []


def test_ai_failure_becomes_a_friendly_503(client, alice, create_task):
    create_task(alice)

    def broken(_):
        raise RuntimeError("groq exploded: secret details")

    use_model(RunnableLambda(broken))
    res = client.post("/ai/daily-plan", headers=alice)
    assert res.status_code == 503
    assert "secret details" not in res.text


def test_missing_api_key_gives_503(client, alice, monkeypatch):
    from src.utils.settings import settings

    monkeypatch.setattr(settings, "GROQ_API_KEY", None)
    res = client.post("/ai/daily-plan", headers=alice)
    assert res.status_code == 503


def test_rate_limit_after_ten_calls(client, alice):
    use_model(fake_model([]))
    for _ in range(10):
        assert client.post("/ai/daily-plan", headers=alice).status_code == 200
    res = client.post("/ai/daily-plan", headers=alice)
    assert res.status_code == 429
    assert int(res.headers["retry-after"]) > 0


def test_rate_limit_is_per_user(client, alice, bob):
    use_model(fake_model([]))
    for _ in range(10):
        client.post("/ai/daily-plan", headers=alice)
    assert client.post("/ai/daily-plan", headers=alice).status_code == 429
    assert client.post("/ai/daily-plan", headers=bob).status_code == 200


def test_real_groq_model_builds_without_network(monkeypatch):
    """Checks our LangChain wiring is valid, without sending anything to Groq."""
    from src.utils.settings import settings

    monkeypatch.setattr(settings, "GROQ_API_KEY", "dummy-key-for-test")
    assert planner.build_model() is not None


def test_due_date_beats_priority_even_if_the_ai_orders_it_wrongly():
    """Medium task due today must come before a high task due tomorrow."""
    today_medium = task(1, "Due today", "medium", TODAY)
    tomorrow_high = task(2, "Due tomorrow", "high", TODAY + timedelta(days=1))
    # the fake AI puts the high-priority one first (the mistake we saw for real)
    picks = [PlanPick(task_id=2, reason="Important"), PlanPick(task_id=1, reason="Soon")]
    plan = planner.generate_daily_plan([today_medium, tomorrow_high], TODAY, fake_model(picks))
    assert [i.task_id for i in plan.items] == [1, 2]


def test_priority_breaks_ties_on_the_same_due_date():
    low = task(1, "Low", "low", TODAY)
    high = task(2, "High", "high", TODAY)
    picks = [PlanPick(task_id=1, reason="a"), PlanPick(task_id=2, reason="b")]
    plan = planner.generate_daily_plan([low, high], TODAY, fake_model(picks))
    assert [i.task_id for i in plan.items] == [2, 1]


def test_tasks_without_due_date_come_last():
    nodate_high = task(1, "No date", "high", None)
    dated_low = task(2, "Dated", "low", TODAY + timedelta(days=5))
    picks = [PlanPick(task_id=1, reason="a"), PlanPick(task_id=2, reason="b")]
    plan = planner.generate_daily_plan([nodate_high, dated_low], TODAY, fake_model(picks))
    assert [i.task_id for i in plan.items] == [2, 1]
