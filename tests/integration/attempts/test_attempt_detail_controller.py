from typing import Any

from httpx import AsyncClient


def _quiz_payload() -> dict[str, Any]:
    return {
        "title": "Prompt Engineering",
        "description": "Basics of prompts.",
        "questions": [
            {
                "body": "What is a prompt?",
                "explanation": "A prompt is an input to an LLM.",
                "options": [
                    {"body": "An LLM input", "is_correct": True},
                    {"body": "A fruit", "is_correct": False},
                ],
            },
            {
                "body": "Which is better phrasing?",
                "explanation": "Specificity helps.",
                "options": [
                    {"body": "Be specific", "is_correct": True},
                    {"body": "Be vague", "is_correct": False},
                ],
            },
        ],
    }


async def test_get_attempt_detail_for_submitted_returns_full_breakdown(
    client: AsyncClient,
) -> None:
    quiz = (await client.post("/api/v1/quizzes", json=_quiz_payload())).json()
    q1, q2 = quiz["questions"]

    start = await client.post(
        "/api/v1/attempts",
        json={"name": "Alice", "email": "alice@example.com", "quiz_id": quiz["id"]},
    )
    attempt_id = start.json()["id"]
    user_id = start.json()["user"]["id"]

    await client.post(
        f"/api/v1/attempts/{attempt_id}/submit",
        json={
            "answers": [
                {"question_id": q1["id"], "option_id": q1["options"][0]["id"]},  # correct
                {"question_id": q2["id"], "option_id": q2["options"][1]["id"]},  # wrong
            ],
        },
    )

    response = await client.get(f"/api/v1/attempts/{attempt_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == attempt_id
    assert body["user_id"] == user_id
    assert body["quiz_id"] == quiz["id"]
    assert body["quiz_title"] == "Prompt Engineering"
    assert body["score"] == 1
    assert body["total"] == 2
    assert body["percentage"] == 50.0
    assert body["feedback"] is not None
    assert "Keep going" in body["feedback"]
    assert len(body["questions"]) == 2

    # sorted by position
    assert body["questions"][0]["position"] == 1
    assert body["questions"][0]["is_correct"] is True
    assert body["questions"][0]["body"] == "What is a prompt?"
    assert body["questions"][0]["explanation"] == "A prompt is an input to an LLM."

    assert body["questions"][1]["is_correct"] is False
    assert body["questions"][1]["correct_option_id"] == q2["options"][0]["id"]
    assert body["questions"][1]["selected_option_id"] == q2["options"][1]["id"]


async def test_get_attempt_detail_for_unsubmitted_returns_empty_questions(
    client: AsyncClient,
) -> None:
    quiz = (await client.post("/api/v1/quizzes", json=_quiz_payload())).json()
    start = await client.post(
        "/api/v1/attempts",
        json={"name": "Bob", "email": "bob@example.com", "quiz_id": quiz["id"]},
    )
    attempt_id = start.json()["id"]

    response = await client.get(f"/api/v1/attempts/{attempt_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["submitted_at"] is None
    assert body["score"] is None
    assert body["percentage"] is None
    assert body["feedback"] is None
    assert body["questions"] == []
    assert body["total"] == 2


async def test_get_attempt_detail_returns_404_for_unknown_id(client: AsyncClient) -> None:
    response = await client.get("/api/v1/attempts/99999")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "attempt_not_found"
