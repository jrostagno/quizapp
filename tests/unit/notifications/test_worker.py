from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.attempts.models import Attempt
from app.notifications.email import MockEmailSender
from app.notifications.models import Notification, NotificationStatus
from app.notifications.worker import send_email_notification
from app.quizzes.models import Option, Question, Quiz
from app.users.models import User


class _FailingSender:
    async def send(self, payload) -> None:  # noqa: ARG002
        raise RuntimeError("SMTP down")


async def _seed(db_session: AsyncSession) -> Notification:
    user = User(name="Alice", email="alice@example.com")
    db_session.add(user)
    await db_session.flush()

    quiz = Quiz(title="Agents", description="d")
    question = Question(body="Q1?", explanation="exp", position=1)
    question.options = [
        Option(body="A", is_correct=True, position=1),
        Option(body="B", is_correct=False, position=2),
    ]
    quiz.questions = [question]
    db_session.add(quiz)
    await db_session.flush()

    attempt = Attempt(
        user_id=user.id,
        quiz_id=quiz.id,
        submitted_at=datetime.now(UTC),
        score=1,
        percentage=100.0,
    )
    db_session.add(attempt)
    await db_session.flush()

    notification = Notification(
        attempt_id=attempt.id,
        status=NotificationStatus.queued,
    )
    db_session.add(notification)
    await db_session.commit()
    return notification


async def test_worker_marks_notification_sent_on_success(
    test_engine: AsyncEngine, db_session: AsyncSession
) -> None:
    notification = await _seed(db_session)

    session_factory = async_sessionmaker(test_engine, expire_on_commit=False)
    ctx = {
        "session_factory": session_factory,
        "email_sender": MockEmailSender(),
        "job_try": 1,
        "max_tries": 3,
    }

    await send_email_notification(ctx, notification.id)

    await db_session.refresh(notification)
    assert notification.status == NotificationStatus.sent
    assert notification.sent_at is not None


async def test_worker_intermediate_retry_keeps_queued_status(
    test_engine: AsyncEngine, db_session: AsyncSession
) -> None:
    notification = await _seed(db_session)

    session_factory = async_sessionmaker(test_engine, expire_on_commit=False)
    ctx = {
        "session_factory": session_factory,
        "email_sender": _FailingSender(),
        "job_try": 1,  # not the last try
        "max_tries": 3,
    }

    with pytest.raises(RuntimeError):
        await send_email_notification(ctx, notification.id)

    await db_session.refresh(notification)
    assert notification.status == NotificationStatus.queued
    assert notification.retry_count == 1
    assert "SMTP down" in notification.last_error


async def test_worker_final_try_marks_failed(
    test_engine: AsyncEngine, db_session: AsyncSession
) -> None:
    notification = await _seed(db_session)

    session_factory = async_sessionmaker(test_engine, expire_on_commit=False)
    ctx = {
        "session_factory": session_factory,
        "email_sender": _FailingSender(),
        "job_try": 3,  # last try
        "max_tries": 3,
    }

    with pytest.raises(RuntimeError):
        await send_email_notification(ctx, notification.id)

    await db_session.refresh(notification)
    assert notification.status == NotificationStatus.failed
    assert notification.retry_count == 1
    assert "SMTP down" in notification.last_error
