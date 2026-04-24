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


@router.get(
    "/{user_id}/attempts",
    response_model=list[AttemptListItem],
    summary="List a user's quiz attempts",
)
async def list_user_attempts(
    user_id: int,
    service: UserServiceDep,
) -> list[AttemptListItem]:
    """Return every attempt the user has started, newest first.

    Both submitted and in-progress attempts are included. The response is a
    flat list of `AttemptListItem` with the resolved `quiz_title` so the
    client can render history without a second roundtrip.

    Returns `404 user_not_found` if the user doesn't exist.
    """
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


@router.get(
    "/{user_id}/stats",
    response_model=UserStats,
    summary="Get aggregate stats for a user",
)
async def get_user_stats(
    user_id: int,
    service: UserServiceDep,
) -> UserStats:
    """Return `{total_attempts, average_percentage}` for a user.

    - `total_attempts` counts every attempt, including in-progress ones.
    - `average_percentage` is the arithmetic mean of the percentage over
      **submitted** attempts only, rounded to two decimals. It's `null` when
      the user has no submitted attempts yet.

    Returns `404 user_not_found` if the user doesn't exist.
    """
    return await service.get_stats(user_id)
