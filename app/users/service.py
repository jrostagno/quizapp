from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.attempts.models import Attempt
from app.attempts.repository import AttemptRepository
from app.core.errors import UserNotFoundError
from app.users.models import User
from app.users.repository import UserRepository
from app.users.schemas import UserStats


class UserService:
    def __init__(
        self,
        repository: UserRepository,
        attempt_repository: AttemptRepository,
        session: AsyncSession,
    ) -> None:
        self.repository = repository
        self.attempt_repository = attempt_repository
        self.session = session

    async def upsert_by_email(self, *, name: str, email: str) -> User:
        return await self.repository.upsert_by_email(name=name, email=email)

    async def get_by_id(self, user_id: int) -> User:
        user = await self.repository.get_by_id(user_id)
        if user is None:
            raise UserNotFoundError(user_id)
        return user

    async def list_attempts(self, user_id: int) -> Sequence[Attempt]:
        await self.get_by_id(user_id)
        return await self.attempt_repository.list_by_user(user_id)

    async def get_stats(self, user_id: int) -> UserStats:
        await self.get_by_id(user_id)
        total, avg = await self.attempt_repository.stats_for_user(user_id)
        return UserStats(
            user_id=user_id,
            total_attempts=total,
            average_percentage=round(avg, 2) if avg is not None else None,
        )
