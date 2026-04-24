from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.quizzes.models import Question, Quiz


class QuizRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_all(self) -> Sequence[Quiz]:
        stmt = select(Quiz).order_by(Quiz.id)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_by_id(self, quiz_id: int) -> Quiz | None:
        stmt = (
            select(Quiz)
            .where(Quiz.id == quiz_id)
            .options(selectinload(Quiz.questions).selectinload(Question.options))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def add(self, quiz: Quiz) -> Quiz:
        self.session.add(quiz)
        await self.session.flush()
        return quiz
