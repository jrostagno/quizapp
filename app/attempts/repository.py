from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.attempts.models import Answer, Attempt
from app.quizzes.models import Question, Quiz


class AttemptRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, attempt: Attempt) -> Attempt:
        self.session.add(attempt)
        await self.session.flush()
        return attempt

    async def get_with_quiz(self, attempt_id: int) -> Attempt | None:
        stmt = (
            select(Attempt)
            .where(Attempt.id == attempt_id)
            .options(
                selectinload(Attempt.quiz)
                .selectinload(Quiz.questions)
                .selectinload(Question.options),
                selectinload(Attempt.user),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    def add_answers(self, answers: list[Answer]) -> None:
        self.session.add_all(answers)
