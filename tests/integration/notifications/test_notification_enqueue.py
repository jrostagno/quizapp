from typing import Any

from arq.connections import ArqRedis
from arq.jobs import Job, JobStatus
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.notifications.models import Notification, NotificationStatus


def _quiz_payload() -> dict[str, Any]:
    return {
        "title": "Agent Fundamentals",
        "description": "A quiz.",
        "questions": [
            {
                "body": "What is an agent?",
                "explanation": "An agent acts.",
                "options": [
                    {"body": "A program", "is_correct": True},
                    {"body": "A fruit", "is_correct": False},
                ],
            }
        ],
    }


async def _setup_and_submit(client: AsyncClient) -> int:
    create = await client.post("/api/v1/quizzes", json=_quiz_payload())
    quiz = create.json()
    q1 = quiz["questions"][0]

    start = await client.post(
        "/api/v1/attempts",
        json={"name": "Alice", "email": "alice@example.com", "quiz_id": quiz["id"]},
    )
    attempt_id = start.json()["id"]

    submit = await client.post(
        f"/api/v1/attempts/{attempt_id}/submit",
        json={
            "answers": [
                {"question_id": q1["id"], "option_id": q1["options"][0]["id"]},
            ],
        },
    )
    assert submit.status_code == 200
    return attempt_id


async def test_submit_enqueues_real_arq_job(
    client: AsyncClient,
    db_session: AsyncSession,
    test_arq_pool: ArqRedis,
) -> None:
    attempt_id = await _setup_and_submit(client)

    # Notification row persisted with status=queued (enqueue succeeded).
    notification = (
        await db_session.execute(select(Notification).where(Notification.attempt_id == attempt_id))
    ).scalar_one()
    assert notification.status == NotificationStatus.queued
    assert notification.last_error is None

    # Actual arq job exists in Redis.
    job = Job(f"notification:{notification.id}", redis=test_arq_pool)
    status = await job.status()
    assert status in {JobStatus.queued, JobStatus.deferred, JobStatus.in_progress}
