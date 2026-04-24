from typing import Any

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.notifications.models import Notification, NotificationStatus


def _quiz_payload_two_questions() -> dict[str, Any]:
    return {
        "title": "Agent Fundamentals",
        "description": "Test quiz for submit endpoint.",
        "questions": [
            {
                "body": "What is an agent?",
                "explanation": "An agent acts on behalf of a user.",
                "options": [
                    {"body": "A program", "is_correct": True},
                    {"body": "A fruit", "is_correct": False},
                ],
            },
            {
                "body": "Which pattern combines reasoning and acting?",
                "explanation": "ReAct is the pattern.",
                "options": [
                    {"body": "ReAct", "is_correct": True},
                    {"body": "Snack", "is_correct": False},
                    {"body": "Rest", "is_correct": False},
                ],
            },
        ],
    }


async def _setup_attempt(client: AsyncClient) -> dict[str, Any]:
    create = await client.post("/api/v1/quizzes", json=_quiz_payload_two_questions())
    quiz = create.json()
    quiz_id = quiz["id"]

    # Options come back in insertion order (via ORM order_by position).
    # Correct options were the FIRST one of each question.
    q1 = quiz["questions"][0]
    q2 = quiz["questions"][1]
    q1_correct_option_id = q1["options"][0]["id"]
    q1_wrong_option_id = q1["options"][1]["id"]
    q2_correct_option_id = q2["options"][0]["id"]
    q2_wrong_option_id = q2["options"][1]["id"]

    start = await client.post(
        "/api/v1/attempts",
        json={"name": "Alice", "email": "alice@example.com", "quiz_id": quiz_id},
    )
    attempt_id = start.json()["id"]

    return {
        "attempt_id": attempt_id,
        "quiz_id": quiz_id,
        "q1_id": q1["id"],
        "q1_correct": q1_correct_option_id,
        "q1_wrong": q1_wrong_option_id,
        "q2_id": q2["id"],
        "q2_correct": q2_correct_option_id,
        "q2_wrong": q2_wrong_option_id,
    }


async def test_submit_all_correct_returns_full_score_and_top_feedback(
    client: AsyncClient,
) -> None:
    ctx = await _setup_attempt(client)

    response = await client.post(
        f"/api/v1/attempts/{ctx['attempt_id']}/submit",
        json={
            "answers": [
                {"question_id": ctx["q1_id"], "option_id": ctx["q1_correct"]},
                {"question_id": ctx["q2_id"], "option_id": ctx["q2_correct"]},
            ],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["attempt_id"] == ctx["attempt_id"]
    assert body["score"] == 2
    assert body["total"] == 2
    assert body["percentage"] == 100.0
    assert "Great job" in body["feedback"]
    assert len(body["questions"]) == 2
    for item in body["questions"]:
        assert item["is_correct"] is True
        assert item["explanation"]


async def test_submit_half_correct_returns_lowest_feedback_tier(client: AsyncClient) -> None:
    ctx = await _setup_attempt(client)

    response = await client.post(
        f"/api/v1/attempts/{ctx['attempt_id']}/submit",
        json={
            "answers": [
                {"question_id": ctx["q1_id"], "option_id": ctx["q1_correct"]},
                {"question_id": ctx["q2_id"], "option_id": ctx["q2_wrong"]},
            ],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["score"] == 1
    assert body["percentage"] == 50.0
    assert "Keep going" in body["feedback"]


async def test_submit_same_attempt_twice_returns_409(client: AsyncClient) -> None:
    ctx = await _setup_attempt(client)
    payload = {
        "answers": [
            {"question_id": ctx["q1_id"], "option_id": ctx["q1_correct"]},
            {"question_id": ctx["q2_id"], "option_id": ctx["q2_correct"]},
        ],
    }

    first = await client.post(f"/api/v1/attempts/{ctx['attempt_id']}/submit", json=payload)
    second = await client.post(f"/api/v1/attempts/{ctx['attempt_id']}/submit", json=payload)

    assert first.status_code == 200
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "attempt_already_submitted"


async def test_submit_unknown_attempt_returns_404(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/attempts/99999/submit",
        json={"answers": [{"question_id": 1, "option_id": 1}]},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "attempt_not_found"


async def test_submit_duplicate_question_returns_422(client: AsyncClient) -> None:
    ctx = await _setup_attempt(client)

    response = await client.post(
        f"/api/v1/attempts/{ctx['attempt_id']}/submit",
        json={
            "answers": [
                {"question_id": ctx["q1_id"], "option_id": ctx["q1_correct"]},
                {"question_id": ctx["q1_id"], "option_id": ctx["q1_wrong"]},
            ],
        },
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_answer_submission"


async def test_submit_missing_question_returns_422(client: AsyncClient) -> None:
    ctx = await _setup_attempt(client)

    response = await client.post(
        f"/api/v1/attempts/{ctx['attempt_id']}/submit",
        json={
            "answers": [
                {"question_id": ctx["q1_id"], "option_id": ctx["q1_correct"]},
            ],
        },
    )

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "invalid_answer_submission"
    assert ctx["q2_id"] in body["error"]["details"]["missing"]


async def test_submit_option_from_wrong_question_returns_422(client: AsyncClient) -> None:
    ctx = await _setup_attempt(client)

    response = await client.post(
        f"/api/v1/attempts/{ctx['attempt_id']}/submit",
        json={
            "answers": [
                {"question_id": ctx["q1_id"], "option_id": ctx["q2_correct"]},
                {"question_id": ctx["q2_id"], "option_id": ctx["q2_correct"]},
            ],
        },
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_answer_submission"


async def test_submit_creates_queued_notification_row(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    ctx = await _setup_attempt(client)

    response = await client.post(
        f"/api/v1/attempts/{ctx['attempt_id']}/submit",
        json={
            "answers": [
                {"question_id": ctx["q1_id"], "option_id": ctx["q1_correct"]},
                {"question_id": ctx["q2_id"], "option_id": ctx["q2_correct"]},
            ],
        },
    )
    assert response.status_code == 200

    result = await db_session.execute(
        select(Notification).where(Notification.attempt_id == ctx["attempt_id"])
    )
    notification = result.scalar_one()
    assert notification.status == NotificationStatus.queued
    assert notification.retry_count == 0
    assert notification.sent_at is None
