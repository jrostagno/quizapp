import logging

from arq.connections import ArqRedis
from sqlalchemy.ext.asyncio import AsyncSession

from app.notifications.models import Notification, NotificationStatus
from app.notifications.repository import NotificationRepository

logger = logging.getLogger(__name__)


class NotificationService:
    def __init__(
        self,
        repository: NotificationRepository,
        session: AsyncSession,
        arq_pool: ArqRedis | None,
    ) -> None:
        self.repository = repository
        self.session = session
        self.arq_pool = arq_pool

    async def queue_for_attempt(self, attempt_id: int) -> Notification:
        """Persist a queued Notification row and enqueue its email job.

        Submission must not fail when the broker is unavailable: on any
        enqueue failure the row is marked `failed_to_enqueue` and the
        caller keeps going.
        """
        notification = await self.repository.create_queued(attempt_id)

        if self.arq_pool is None:
            notification.status = NotificationStatus.failed_to_enqueue
            notification.last_error = "arq pool is not available"
            await self.session.flush()
            logger.warning(
                "arq pool unavailable — notification not enqueued",
                extra={"notification_id": notification.id},
            )
            return notification

        try:
            await self.arq_pool.enqueue_job(
                "send_email_notification",
                notification.id,
                _job_id=f"notification:{notification.id}",
            )
        except Exception as exc:
            notification.status = NotificationStatus.failed_to_enqueue
            notification.last_error = str(exc)[:1024]
            await self.session.flush()
            logger.exception(
                "failed to enqueue notification job",
                extra={"notification_id": notification.id},
            )

        return notification
