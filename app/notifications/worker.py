import logging
from datetime import UTC, datetime
from typing import Any

from arq.connections import RedisSettings
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import selectinload

from app.attempts.models import Attempt
from app.attempts.scoring import feedback_for_percentage
from app.core.config import get_settings
from app.notifications.email import MockEmailSender, build_payload
from app.notifications.models import Notification, NotificationStatus
from app.quizzes.models import Quiz
from app.users import models as _users_models  # noqa: F401 — register User mapper

logger = logging.getLogger(__name__)


async def startup(ctx: dict[str, Any]) -> None:
    settings = get_settings()
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    ctx["engine"] = engine
    ctx["session_factory"] = async_sessionmaker(engine, expire_on_commit=False)
    ctx["email_sender"] = MockEmailSender()


async def shutdown(ctx: dict[str, Any]) -> None:
    engine = ctx.get("engine")
    if engine is not None:
        await engine.dispose()


async def send_email_notification(ctx: dict[str, Any], notification_id: int) -> None:
    session_factory = ctx["session_factory"]
    email_sender = ctx["email_sender"]
    job_try = ctx.get("job_try", 1)
    max_tries = ctx.get("max_tries", 3)

    async with session_factory() as session:
        stmt = (
            select(Notification)
            .where(Notification.id == notification_id)
            .options(
                selectinload(Notification.attempt).selectinload(Attempt.user),
                selectinload(Notification.attempt)
                .selectinload(Attempt.quiz)
                .selectinload(Quiz.questions),
            )
        )
        result = await session.execute(stmt)
        notification = result.scalar_one_or_none()
        if notification is None:
            logger.warning("notification not found", extra={"notification_id": notification_id})
            return

        attempt = notification.attempt
        user = attempt.user
        quiz = attempt.quiz

        percentage = attempt.percentage or 0.0
        payload = build_payload(
            user_name=user.name,
            user_email=user.email,
            quiz_title=quiz.title,
            score=attempt.score or 0,
            total=len(quiz.questions),
            percentage=percentage,
            feedback=feedback_for_percentage(percentage),
            submitted_at=attempt.submitted_at or datetime.now(UTC),
        )

        try:
            await email_sender.send(payload)
        except Exception as exc:
            notification.retry_count += 1
            notification.last_error = str(exc)[:1024]
            if job_try >= max_tries:
                notification.status = NotificationStatus.failed
            await session.commit()
            raise

        notification.status = NotificationStatus.sent
        notification.sent_at = datetime.now(UTC)
        await session.commit()


class WorkerSettings:
    functions = [send_email_notification]
    on_startup = startup
    on_shutdown = shutdown
    max_tries = 3
    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)
