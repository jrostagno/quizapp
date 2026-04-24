from sqlalchemy.ext.asyncio import AsyncSession

from app.attempts.models import Attempt
from app.attempts.repository import AttemptRepository
from app.attempts.schemas import AttemptStartRequest
from app.quizzes.models import Quiz
from app.quizzes.service import QuizService
from app.users.models import User
from app.users.service import UserService


class AttemptService:
    def __init__(
        self,
        repository: AttemptRepository,
        user_service: UserService,
        quiz_service: QuizService,
        session: AsyncSession,
    ) -> None:
        self.repository = repository
        self.user_service = user_service
        self.quiz_service = quiz_service
        self.session = session

    async def start_attempt(self, data: AttemptStartRequest) -> tuple[Attempt, User, Quiz]:
        quiz = await self.quiz_service.get_quiz(data.quiz_id)
        user = await self.user_service.upsert_by_email(name=data.name, email=data.email)

        attempt = Attempt(user_id=user.id, quiz_id=quiz.id)
        await self.repository.add(attempt)
        await self.session.commit()
        await self.session.refresh(attempt)

        return attempt, user, quiz
