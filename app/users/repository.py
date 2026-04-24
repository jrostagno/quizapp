from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.users.models import User


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_email(self, email: str) -> User | None:
        stmt = select(User).where(User.email == email)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: int) -> User | None:
        stmt = select(User).where(User.id == user_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def upsert_by_email(self, name: str, email: str) -> User:
        existing = await self.get_by_email(email)
        if existing is not None:
            existing.name = name
            await self.session.flush()
            return existing

        user = User(name=name, email=email)
        self.session.add(user)
        await self.session.flush()
        return user
