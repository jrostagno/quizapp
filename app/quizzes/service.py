from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import InvalidQuizStructureError, QuizNotFoundError
from app.quizzes.models import Option, Question, Quiz
from app.quizzes.repository import QuizRepository
from app.quizzes.schemas import QuizCreate


class QuizService:
    def __init__(self, repository: QuizRepository, session: AsyncSession) -> None:
        self.repository = repository
        self.session = session

    async def list_quizzes(self) -> Sequence[Quiz]:
        return await self.repository.list_all()

    async def get_quiz(self, quiz_id: int) -> Quiz:
        quiz = await self.repository.get_by_id(quiz_id)
        if quiz is None:
            raise QuizNotFoundError(quiz_id)
        return quiz

    async def create_quiz(self, data: QuizCreate) -> Quiz:
        self._validate_structure(data)

        quiz = Quiz(title=data.title, description=data.description)
        for q_idx, q_data in enumerate(data.questions, start=1):
            question = Question(
                body=q_data.body,
                explanation=q_data.explanation,
                position=q_data.position if q_data.position is not None else q_idx,
            )
            for o_idx, o_data in enumerate(q_data.options, start=1):
                question.options.append(
                    Option(
                        body=o_data.body,
                        is_correct=o_data.is_correct,
                        position=o_data.position if o_data.position is not None else o_idx,
                    )
                )
            quiz.questions.append(question)

        await self.repository.add(quiz)
        await self.session.commit()

        created = await self.repository.get_by_id(quiz.id)
        assert created is not None
        return created

    @staticmethod
    def _validate_structure(data: QuizCreate) -> None:
        for idx, question in enumerate(data.questions, start=1):
            correct = sum(1 for option in question.options if option.is_correct)
            if correct != 1:
                raise InvalidQuizStructureError(
                    f"Question {idx} must have exactly one correct option, got {correct}.",
                    details={"question_index": idx, "correct_count": correct},
                )
