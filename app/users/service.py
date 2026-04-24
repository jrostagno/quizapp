from sqlalchemy.ext.asyncio import AsyncSession

from app.users.models import User
from app.users.repository import UserRepository


class UserService:
    def __init__(self, repository: UserRepository, session: AsyncSession) -> None:
        self.repository = repository
        self.session = session

    async def upsert_by_email(self, *, name: str, email: str) -> User:
        return await self.repository.upsert_by_email(name=name, email=email)
