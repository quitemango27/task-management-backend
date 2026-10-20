"""Tests for the AI task breakdown ("Prepare for exam" -> small steps).

As in test_ai.py, the real Groq model is never called: a fake model returns a fixed
answer, while the real prompt and the real clean-up code still run.
"""
import pytest
from langchain_core.runnables import RunnableLambda

from main import app
from src.ai import limiter, planner
from src.ai.dtos import AIBreakdown, AIStep
from src.ai.router import get_breakdown_model, get_plan_model


def fake_model(steps, seen=None):
    def respond(prompt_value):
        if seen is not None:
            seen.append(prompt_value.to_string())
        return AIBreakdown(steps=[AIStep(title=t, priority=p) for t, p in steps])

    return RunnableLambda(respond)


@pytest.fixture(autouse=True)
def clean_state():
    limiter.reset()
    yield
    app.dependency_overrides.pop(get_breakdown_model, None)
    app.dependency_overrides.pop(get_plan_model, None)
    limiter.reset()


def use_model(model):
    app.dependency_overrides[get_breakdown_model] = lambda: model


STEPS = [("Make a study schedule", "high"), ("Review chapter 1", "medium"), ("Take a practice test", "low")]


# ---------- the planner on its own ----------

def test_steps_keep_the_ais_order_and_priorities():
    out = planner.generate_breakdown("Prepare for exam", "", fake_model(STEPS))
    assert [(s.title, s.priority) for s in out.steps] == STEPS


def test_prompt_contains_the_goal_and_details():
    seen = []
    planner.generate_breakdown("Prepare for exam", "Maths, 3 chapters", fake_model(STEPS, seen=seen))
    assert "Goal: Prepare for exam" in seen[0]
    assert "Details: Maths, 3 chapters" in seen[0]


def test_numbering_and_bullets_are_removed():
    out = planner.generate_breakdown("Goal", "", fake_model([("1. First", "low"), ("- Second", "low"), ("• Third", "low")]))
    assert [s.title for s in out.steps] == ["First", "Second", "Third"]


def test_long_titles_are_cut_to_100_characters():
    out = planner.generate_breakdown("Goal", "", fake_model([("x" * 300, "low")]))
    assert len(out.steps[0].title) == 100


def test_duplicates_empty_and_the_goal_itself_are_dropped():
    steps = [("Prepare for exam", "high"), ("Read notes", "low"), ("read NOTES", "low"), ("   ", "low")]
    out = planner.generate_breakdown("Prepare for exam", "", fake_model(steps))
    assert [s.title for s in out.steps] == ["Read notes"]


def test_at_most_six_steps():
    out = planner.generate_breakdown("Goal", "", fake_model([(f"Step {i}", "low") for i in range(1, 11)]))
    assert len(out.steps) == 6


def test_unknown_priority_becomes_medium():
    out = planner.generate_breakdown("Goal", "", fake_model([("Do it", "URGENT!!"), ("Do more", " High ")]))
    assert [s.priority for s in out.steps] == ["medium", "high"]


def test_no_usable_steps_is_an_error():
    with pytest.raises(ValueError):
        planner.generate_breakdown("Goal", "", fake_model([("   ", "low")]))


# ---------- the API endpoint ----------

def test_breakdown_requires_login(client):
    use_model(fake_model(STEPS))
    assert client.post("/ai/breakdown", json={"title": "x"}).status_code == 401


def test_breakdown_end_to_end(client, alice):
    use_model(fake_model(STEPS))
    res = client.post("/ai/breakdown", json={"title": "Prepare for exam"}, headers=alice)
    assert res.status_code == 200
    assert res.json() == {"steps": [{"title": t, "priority": p} for t, p in STEPS]}


def test_breakdown_does_not_create_any_tasks(client, alice):
    use_model(fake_model(STEPS))
    client.post("/ai/breakdown", json={"title": "Prepare for exam"}, headers=alice)
    assert client.get("/tasks/all_tasks", headers=alice).json() == []


def test_other_peoples_tasks_never_reach_the_ai(client, alice, bob, create_task):
    create_task(bob, title="Bob secret plan")
    seen = []
    use_model(fake_model(STEPS, seen=seen))
    client.post("/ai/breakdown", json={"title": "Prepare for exam"}, headers=alice)
    assert "Bob secret plan" not in seen[0]


@pytest.mark.parametrize(
    "body",
    [{}, {"title": ""}, {"title": "   "}, {"title": "x" * 101}, {"title": "ok", "details": "y" * 201}],
)
def test_bad_input_is_rejected(client, alice, body):
    use_model(fake_model(STEPS))
    assert client.post("/ai/breakdown", json=body, headers=alice).status_code == 422


def test_ai_failure_becomes_a_friendly_503(client, alice):
    def broken(_):
        raise RuntimeError("groq exploded: secret details")

    use_model(RunnableLambda(broken))
    res = client.post("/ai/breakdown", json={"title": "Goal"}, headers=alice)
    assert res.status_code == 503
    assert "secret details" not in res.text


def test_an_empty_ai_answer_becomes_a_503(client, alice):
    use_model(fake_model([]))
    assert client.post("/ai/breakdown", json={"title": "Goal"}, headers=alice).status_code == 503


def test_missing_api_key_gives_503(client, alice, monkeypatch):
    from src.utils.settings import settings

    monkeypatch.setattr(settings, "GROQ_API_KEY", None)
    assert client.post("/ai/breakdown", json={"title": "Goal"}, headers=alice).status_code == 503


def test_rate_limit_after_fifteen_calls_and_plans_are_unaffected(client, alice):
    use_model(fake_model(STEPS))
    app.dependency_overrides[get_plan_model] = lambda: RunnableLambda(lambda _: None)
    for _ in range(15):
        assert client.post("/ai/breakdown", json={"title": "Goal"}, headers=alice).status_code == 200
    res = client.post("/ai/breakdown", json={"title": "Goal"}, headers=alice)
    assert res.status_code == 429 and int(res.headers["retry-after"]) > 0
    # the daily-plan feature has its own bucket
    assert client.post("/ai/daily-plan", headers=alice).status_code == 200


def test_breakdown_rate_limit_is_per_user(client, alice, bob):
    use_model(fake_model(STEPS))
    for _ in range(15):
        client.post("/ai/breakdown", json={"title": "Goal"}, headers=alice)
    assert client.post("/ai/breakdown", json={"title": "Goal"}, headers=alice).status_code == 429
    assert client.post("/ai/breakdown", json={"title": "Goal"}, headers=bob).status_code == 200


def test_real_groq_breakdown_model_builds_without_network(monkeypatch):
    from src.utils.settings import settings

    monkeypatch.setattr(settings, "GROQ_API_KEY", "dummy-key-for-test")
    assert planner.build_model(AIBreakdown) is not None
