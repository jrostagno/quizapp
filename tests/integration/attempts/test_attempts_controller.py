from typing import Any

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.users.models import User


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
            }
        ],
    }


async def _create_quiz(client: AsyncClient, title: str = "Agent Fundamentals") -> int:
    response = await client.post("/api/v1/quizzes", json=_quiz_payload(title))
    assert response.status_code == 201
    return response.json()["id"]


async def test_start_attempt_creates_user_and_hides_correct_answers(client: AsyncClient) -> None:
    quiz_id = await _create_quiz(client)

    response = await client.post(
        "/api/v1/attempts",
        json={"name": "Alice", "email": "alice@example.com", "quiz_id": quiz_id},
    )

    assert response.status_code == 201
    body = response.json()

    assert body["id"] >= 1
    assert "started_at" in body

    assert body["user"]["name"] == "Alice"
    assert body["user"]["email"] == "alice@example.com"

    assert body["quiz"]["id"] == quiz_id
    first_question = body["quiz"]["questions"][0]
    assert "explanation" not in first_question
    for option in first_question["options"]:
        assert "is_correct" not in option


async def test_start_attempt_reuses_user_and_updates_name(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    quiz_id = await _create_quiz(client)

    first = await client.post(
        "/api/v1/attempts",
        json={"name": "Alice", "email": "alice@example.com", "quiz_id": quiz_id},
    )
    second = await client.post(
        "/api/v1/attempts",
        json={"name": "Alice Renamed", "email": "alice@example.com", "quiz_id": quiz_id},
    )

    assert first.status_code == 201
    assert second.status_code == 201

    # Same user, different attempt ids
    assert first.json()["user"]["id"] == second.json()["user"]["id"]
    assert first.json()["id"] != second.json()["id"]

    # Name was updated (last-write-wins)
    result = await db_session.execute(select(User).where(User.email == "alice@example.com"))
    user = result.scalar_one()
    assert user.name == "Alice Renamed"


async def test_start_attempt_returns_404_for_unknown_quiz(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/attempts",
        json={"name": "Alice", "email": "alice@example.com", "quiz_id": 99999},
    )

    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "quiz_not_found"


async def test_start_attempt_returns_422_for_invalid_email(client: AsyncClient) -> None:
    quiz_id = await _create_quiz(client)

    response = await client.post(
        "/api/v1/attempts",
        json={"name": "Alice", "email": "not-an-email", "quiz_id": quiz_id},
    )

    assert response.status_code == 422


async def test_start_attempt_persists_user_row(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    quiz_id = await _create_quiz(client)

    await client.post(
        "/api/v1/attempts",
        json={"name": "Bob", "email": "bob@example.com", "quiz_id": quiz_id},
    )

    result = await db_session.execute(select(User).where(User.email == "bob@example.com"))
    user = result.scalar_one()
    assert user.name == "Bob"
