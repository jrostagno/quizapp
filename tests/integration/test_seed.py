from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.quizzes.models import Question, Quiz
from scripts.seed import QUIZZES, seed_quizzes


async def test_seed_creates_expected_quizzes_and_questions(db_session: AsyncSession) -> None:
    created = await seed_quizzes(db_session)
    assert len(created) == len(QUIZZES)

    quizzes = (
        (
            await db_session.execute(
                select(Quiz)
                .options(selectinload(Quiz.questions).selectinload(Question.options))
                .order_by(Quiz.id)
            )
        )
        .scalars()
        .all()
    )

    titles = {quiz.title for quiz in quizzes}
    assert titles == {"Agent Fundamentals", "Prompt Engineering Basics"}

    for quiz in quizzes:
        assert len(quiz.questions) >= 5
        for question in quiz.questions:
            assert len(question.options) >= 2
            correct = [opt for opt in question.options if opt.is_correct]
            assert len(correct) == 1, (
                f"Question {question.body!r} must have exactly one correct option"
            )


async def test_seed_is_idempotent(db_session: AsyncSession) -> None:
    created_first = await seed_quizzes(db_session)
    created_second = await seed_quizzes(db_session)

    assert len(created_first) == len(QUIZZES)
    assert created_second == []

    total = (await db_session.execute(select(Quiz).order_by(Quiz.id))).scalars().all()
    assert len(total) == len(QUIZZES)
