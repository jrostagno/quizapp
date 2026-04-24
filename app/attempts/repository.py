from collections.abc import Sequence

from sqlalchemy import func, select
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

    async def get_detail(self, attempt_id: int) -> Attempt | None:
        stmt = (
            select(Attempt)
            .where(Attempt.id == attempt_id)
            .options(
                selectinload(Attempt.quiz)
                .selectinload(Quiz.questions)
                .selectinload(Question.options),
                selectinload(Attempt.answers),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_user(self, user_id: int) -> Sequence[Attempt]:
        stmt = (
            select(Attempt)
            .where(Attempt.user_id == user_id)
            .options(selectinload(Attempt.quiz))
            .order_by(Attempt.started_at.desc())
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def stats_for_user(self, user_id: int) -> tuple[int, float | None]:
        total_stmt = select(func.count(Attempt.id)).where(Attempt.user_id == user_id)
        total = (await self.session.execute(total_stmt)).scalar_one()

        avg_stmt = (
            select(func.avg(Attempt.percentage))
            .where(Attempt.user_id == user_id)
            .where(Attempt.submitted_at.is_not(None))
        )
        avg = (await self.session.execute(avg_stmt)).scalar_one_or_none()
        return total, float(avg) if avg is not None else None

    def add_answers(self, answers: list[Answer]) -> None:
        self.session.add_all(answers)
