from sqlalchemy.ext.asyncio import AsyncSession

from app.notifications.models import Notification, NotificationStatus


class NotificationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_queued(self, attempt_id: int) -> Notification:
        notification = Notification(
            attempt_id=attempt_id,
            status=NotificationStatus.queued,
        )
        self.session.add(notification)
        await self.session.flush()
        return notification
