from typing import Any

from httpx import AsyncClient


def _quiz_payload(title: str = "Agent Fundamentals") -> dict[str, Any]:
    return {
        "title": title,
        "description": f"Basics of {title}.",
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
                "body": "Which is a common agent pattern?",
                "explanation": "ReAct combines reasoning and acting.",
                "options": [
                    {"body": "ReAct", "is_correct": True},
                    {"body": "Snack", "is_correct": False},
                    {"body": "Rest", "is_correct": False},
                ],
            },
        ],
    }


async def test_post_quiz_creates_and_hides_correct_answers(client: AsyncClient) -> None:
    response = await client.post("/api/v1/quizzes", json=_quiz_payload())

    assert response.status_code == 201
    body = response.json()
    assert body["title"] == "Agent Fundamentals"
    assert len(body["questions"]) == 2

    first_question = body["questions"][0]
    assert "explanation" not in first_question
    assert first_question["position"] == 1
    assert len(first_question["options"]) == 2
    for option in first_question["options"]:
        assert "is_correct" not in option


async def test_get_quiz_returns_detail(client: AsyncClient) -> None:
    created = await client.post("/api/v1/quizzes", json=_quiz_payload("Prompt Engineering"))
    quiz_id = created.json()["id"]

    response = await client.get(f"/api/v1/quizzes/{quiz_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == quiz_id
    assert body["title"] == "Prompt Engineering"
    assert len(body["questions"]) == 2


async def test_get_quiz_returns_404_for_unknown_id(client: AsyncClient) -> None:
    response = await client.get("/api/v1/quizzes/99999")

    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "quiz_not_found"
    assert body["error"]["details"] == {"quiz_id": 99999}


async def test_list_quizzes_returns_list_items_without_questions(client: AsyncClient) -> None:
    for title in ["Quiz A", "Quiz B"]:
        await client.post("/api/v1/quizzes", json=_quiz_payload(title))

    response = await client.get("/api/v1/quizzes")

    assert response.status_code == 200
    items = response.json()
    assert len(items) == 2
    titles = {item["title"] for item in items}
    assert titles == {"Quiz A", "Quiz B"}
    for item in items:
        assert "questions" not in item


async def test_post_quiz_rejects_question_without_correct_option(client: AsyncClient) -> None:
    payload = _quiz_payload()
    for option in payload["questions"][0]["options"]:
        option["is_correct"] = False

    response = await client.post("/api/v1/quizzes", json=payload)

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "invalid_quiz_structure"
    assert body["error"]["details"]["question_index"] == 1
    assert body["error"]["details"]["correct_count"] == 0
