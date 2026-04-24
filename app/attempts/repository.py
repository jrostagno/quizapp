from sqlalchemy.ext.asyncio import AsyncSession

from app.attempts.models import Attempt


class AttemptRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, attempt: Attempt) -> Attempt:
        self.session.add(attempt)
        await self.session.flush()
        return attempt
