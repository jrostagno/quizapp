from typing import Any

from httpx import AsyncClient


def _quiz_payload(title: str = "Agent Fundamentals") -> dict[str, Any]:
    return {
        "title": title,
        "description": f"Basics of {title}.",
        "questions": [
            {
                "body": "Q1?",
                "explanation": "E1",
                "options": [
                    {"body": "A", "is_correct": True},
                    {"body": "B", "is_correct": False},
                ],
            },
            {
                "body": "Q2?",
                "explanation": "E2",
                "options": [
                    {"body": "X", "is_correct": False},
                    {"body": "Y", "is_correct": True},
                ],
            },
        ],
    }


async def _create_quiz(client: AsyncClient) -> dict[str, Any]:
    response = await client.post("/api/v1/quizzes", json=_quiz_payload())
    assert response.status_code == 201
    return response.json()


async def _start_attempt(
    client: AsyncClient, quiz_id: int, email: str, name: str = "Alice"
) -> dict[str, Any]:
    response = await client.post(
        "/api/v1/attempts",
        json={"name": name, "email": email, "quiz_id": quiz_id},
    )
    assert response.status_code == 201
    return response.json()


async def _submit_all_correct(client: AsyncClient, attempt_id: int, quiz: dict[str, Any]) -> None:
    q1 = quiz["questions"][0]
    q2 = quiz["questions"][1]
    response = await client.post(
        f"/api/v1/attempts/{attempt_id}/submit",
        json={
            "answers": [
                {"question_id": q1["id"], "option_id": q1["options"][0]["id"]},
                {"question_id": q2["id"], "option_id": q2["options"][1]["id"]},
            ],
        },
    )
    assert response.status_code == 200


async def _submit_half_correct(client: AsyncClient, attempt_id: int, quiz: dict[str, Any]) -> None:
    q1 = quiz["questions"][0]
    q2 = quiz["questions"][1]
    response = await client.post(
        f"/api/v1/attempts/{attempt_id}/submit",
        json={
            "answers": [
                {"question_id": q1["id"], "option_id": q1["options"][0]["id"]},
                {"question_id": q2["id"], "option_id": q2["options"][0]["id"]},
            ],
        },
    )
    assert response.status_code == 200


async def test_list_user_attempts_returns_history(client: AsyncClient) -> None:
    quiz = await _create_quiz(client)
    first = await _start_attempt(client, quiz["id"], "alice@example.com")
    user_id = first["user"]["id"]
    await _submit_all_correct(client, first["id"], quiz)

    second = await _start_attempt(client, quiz["id"], "alice@example.com")
    # leave second unsubmitted

    response = await client.get(f"/api/v1/users/{user_id}/attempts")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 2
    # Ordered by started_at DESC — unsubmitted (just started) comes first
    assert body[0]["id"] == second["id"]
    assert body[0]["submitted_at"] is None
    assert body[0]["score"] is None
    assert body[0]["quiz_title"] == "Agent Fundamentals"
    assert body[1]["id"] == first["id"]
    assert body[1]["submitted_at"] is not None
    assert body[1]["score"] == 2


async def test_list_user_attempts_returns_404_for_unknown_user(client: AsyncClient) -> None:
    response = await client.get("/api/v1/users/99999/attempts")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "user_not_found"


async def test_get_user_stats_averages_submitted_only(client: AsyncClient) -> None:
    quiz = await _create_quiz(client)
    first = await _start_attempt(client, quiz["id"], "alice@example.com")
    user_id = first["user"]["id"]
    await _submit_all_correct(client, first["id"], quiz)  # 100%

    second = await _start_attempt(client, quiz["id"], "alice@example.com")
    await _submit_half_correct(client, second["id"], quiz)  # 50%

    await _start_attempt(client, quiz["id"], "alice@example.com")
    # leave the third unsubmitted — not counted in average

    response = await client.get(f"/api/v1/users/{user_id}/stats")

    assert response.status_code == 200
    body = response.json()
    assert body["user_id"] == user_id
    assert body["total_attempts"] == 3
    assert body["average_percentage"] == 75.0


async def test_get_user_stats_returns_null_average_when_no_submissions(client: AsyncClient) -> None:
    quiz = await _create_quiz(client)
    started = await _start_attempt(client, quiz["id"], "alice@example.com")
    user_id = started["user"]["id"]

    response = await client.get(f"/api/v1/users/{user_id}/stats")

    assert response.status_code == 200
    body = response.json()
    assert body["total_attempts"] == 1
    assert body["average_percentage"] is None


async def test_get_user_stats_returns_404_for_unknown_user(client: AsyncClient) -> None:
    response = await client.get("/api/v1/users/99999/stats")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "user_not_found"
