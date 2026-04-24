from unittest.mock import AsyncMock

from app.notifications.models import Notification, NotificationStatus
from app.notifications.service import NotificationService


def _notification(id: int = 42) -> Notification:
    return Notification(id=id, attempt_id=1, status=NotificationStatus.queued)


async def test_queue_enqueues_job_when_pool_is_available() -> None:
    repository = AsyncMock()
    session = AsyncMock()
    pool = AsyncMock()
    repository.create_queued.return_value = _notification(id=42)

    service = NotificationService(repository, session, pool)

    result = await service.queue_for_attempt(attempt_id=1)

    repository.create_queued.assert_awaited_once_with(1)
    pool.enqueue_job.assert_awaited_once_with(
        "send_email_notification", 42, _job_id="notification:42"
    )
    assert result.status == NotificationStatus.queued


async def test_queue_marks_failed_to_enqueue_when_pool_is_none() -> None:
    repository = AsyncMock()
    session = AsyncMock()
    repository.create_queued.return_value = _notification()

    service = NotificationService(repository, session, None)

    result = await service.queue_for_attempt(attempt_id=1)

    assert result.status == NotificationStatus.failed_to_enqueue
    assert result.last_error == "arq pool is not available"
    session.flush.assert_awaited()


async def test_queue_marks_failed_to_enqueue_when_enqueue_raises() -> None:
    repository = AsyncMock()
    session = AsyncMock()
    pool = AsyncMock()
    pool.enqueue_job.side_effect = ConnectionError("redis down")
    repository.create_queued.return_value = _notification()

    service = NotificationService(repository, session, pool)

    result = await service.queue_for_attempt(attempt_id=1)

    assert result.status == NotificationStatus.failed_to_enqueue
    assert "redis down" in result.last_error.lower()
    session.flush.assert_awaited()
