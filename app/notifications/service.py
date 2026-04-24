from sqlalchemy.ext.asyncio import AsyncSession

from app.notifications.models import Notification
from app.notifications.repository import NotificationRepository


class NotificationService:
    def __init__(self, repository: NotificationRepository, session: AsyncSession) -> None:
        self.repository = repository
        self.session = session

    async def queue_for_attempt(self, attempt_id: int) -> Notification:
        """Create a notification row with status=queued.

        Enqueueing into the arq task broker is added in the next stage; for now
        this guarantees the persistence side of the async flow.
        """
        return await self.repository.create_queued(attempt_id)
