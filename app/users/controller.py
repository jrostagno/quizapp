from typing import Annotated

from fastapi import APIRouter, Depends

from app.attempts.repository import AttemptRepository
from app.attempts.schemas import AttemptListItem
from app.core.deps import SessionDep
from app.users.repository import UserRepository
from app.users.schemas import UserStats
from app.users.service import UserService


def _build_user_service(session: SessionDep) -> UserService:
    return UserService(
        repository=UserRepository(session),
        attempt_repository=AttemptRepository(session),
        session=session,
    )


UserServiceDep = Annotated[UserService, Depends(_build_user_service)]

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/{user_id}/attempts", response_model=list[AttemptListItem])
async def list_user_attempts(
    user_id: int,
    service: UserServiceDep,
) -> list[AttemptListItem]:
    attempts = await service.list_attempts(user_id)
    return [
        AttemptListItem(
            id=attempt.id,
            quiz_id=attempt.quiz_id,
            quiz_title=attempt.quiz.title,
            started_at=attempt.started_at,
            submitted_at=attempt.submitted_at,
            score=attempt.score,
            percentage=attempt.percentage,
        )
        for attempt in attempts
    ]


@router.get("/{user_id}/stats", response_model=UserStats)
async def get_user_stats(
    user_id: int,
    service: UserServiceDep,
) -> UserStats:
    return await service.get_stats(user_id)
