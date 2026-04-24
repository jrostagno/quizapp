from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.attempts.repository import AttemptRepository
from app.attempts.schemas import AttemptStartRequest, AttemptStartResponse
from app.attempts.service import AttemptService
from app.core.deps import SessionDep
from app.quizzes.repository import QuizRepository
from app.quizzes.schemas import QuizDetail
from app.quizzes.service import QuizService
from app.users.repository import UserRepository
from app.users.schemas import UserRead
from app.users.service import UserService


def _build_attempt_service(session: SessionDep) -> AttemptService:
    return AttemptService(
        repository=AttemptRepository(session),
        user_service=UserService(UserRepository(session), session),
        quiz_service=QuizService(QuizRepository(session), session),
        session=session,
    )


AttemptServiceDep = Annotated[AttemptService, Depends(_build_attempt_service)]

router = APIRouter(prefix="/attempts", tags=["attempts"])


@router.post(
    "",
    response_model=AttemptStartResponse,
    status_code=status.HTTP_201_CREATED,
)
async def start_attempt(
    data: AttemptStartRequest,
    service: AttemptServiceDep,
) -> AttemptStartResponse:
    attempt, user, quiz = await service.start_attempt(data)
    return AttemptStartResponse(
        id=attempt.id,
        started_at=attempt.started_at,
        user=UserRead.model_validate(user),
        quiz=QuizDetail.model_validate(quiz),
    )
