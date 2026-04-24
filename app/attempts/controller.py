from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.attempts.repository import AttemptRepository
from app.attempts.schemas import (
    AttemptDetail,
    AttemptResult,
    AttemptStartRequest,
    AttemptStartResponse,
    AttemptSubmitRequest,
)
from app.attempts.service import AttemptService
from app.core.deps import ArqPoolDep, SessionDep
from app.notifications.repository import NotificationRepository
from app.notifications.service import NotificationService
from app.quizzes.repository import QuizRepository
from app.quizzes.schemas import QuizDetail
from app.quizzes.service import QuizService
from app.users.repository import UserRepository
from app.users.schemas import UserRead
from app.users.service import UserService


def _build_attempt_service(session: SessionDep, arq_pool: ArqPoolDep) -> AttemptService:
    attempt_repository = AttemptRepository(session)
    return AttemptService(
        repository=attempt_repository,
        user_service=UserService(UserRepository(session), attempt_repository, session),
        quiz_service=QuizService(QuizRepository(session), session),
        notification_service=NotificationService(
            NotificationRepository(session), session, arq_pool
        ),
        session=session,
    )


AttemptServiceDep = Annotated[AttemptService, Depends(_build_attempt_service)]

router = APIRouter(prefix="/attempts", tags=["attempts"])


@router.post(
    "",
    response_model=AttemptStartResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Start a new quiz attempt",
)
async def start_attempt(
    data: AttemptStartRequest,
    service: AttemptServiceDep,
) -> AttemptStartResponse:
    """Start a new attempt.

    The user is upserted by email: on the first request with a given email a
    new user is created; subsequent requests reuse that user (and update the
    stored `name` to the most recent value).

    The response includes the quiz detail (without correct-answer markers) so
    the client can render the questions immediately without a second roundtrip.

    Returns `404 quiz_not_found` if the quiz doesn't exist.
    """
    attempt, user, quiz = await service.start_attempt(data)
    return AttemptStartResponse(
        id=attempt.id,
        started_at=attempt.started_at,
        user=UserRead.model_validate(user),
        quiz=QuizDetail.model_validate(quiz),
    )


@router.post(
    "/{attempt_id}/submit",
    response_model=AttemptResult,
    summary="Submit answers and receive the score + feedback",
)
async def submit_attempt(
    attempt_id: int,
    data: AttemptSubmitRequest,
    service: AttemptServiceDep,
) -> AttemptResult:
    """Score an attempt.

    Answers must cover **exactly** the quiz's questions (no duplicates, no
    missing, no extras), and each `option_id` must belong to its stated
    `question_id`; otherwise the request fails with
    `422 invalid_answer_submission`.

    On success the attempt is marked submitted, the score/percentage are
    persisted, and a queued notification row is created. The async email
    notification job is enqueued to arq — if Redis is unavailable the row is
    marked `failed_to_enqueue` and the submission still returns 200.

    Returns `404 attempt_not_found` if the id doesn't exist, or
    `409 attempt_already_submitted` if the attempt was previously submitted.
    """
    return await service.submit_attempt(attempt_id, data)


@router.get(
    "/{attempt_id}",
    response_model=AttemptDetail,
    summary="Get an attempt with its per-question breakdown",
)
async def get_attempt_detail(
    attempt_id: int,
    service: AttemptServiceDep,
) -> AttemptDetail:
    """Return the full detail of an attempt.

    For submitted attempts the `questions` array contains the per-question
    breakdown — selected option, correct option, correctness, and the
    explanation. For in-progress attempts `questions` is an empty array and
    `score`/`percentage`/`feedback` are null.

    Returns `404 attempt_not_found` if the id doesn't exist.
    """
    return await service.get_attempt_detail(attempt_id)
