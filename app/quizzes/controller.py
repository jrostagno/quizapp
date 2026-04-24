from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.core.deps import SessionDep
from app.quizzes.repository import QuizRepository
from app.quizzes.schemas import QuizCreate, QuizDetail, QuizListItem
from app.quizzes.service import QuizService


def _build_service(session: SessionDep) -> QuizService:
    return QuizService(QuizRepository(session), session)


QuizServiceDep = Annotated[QuizService, Depends(_build_service)]

router = APIRouter(prefix="/quizzes", tags=["quizzes"])


@router.get(
    "",
    response_model=list[QuizListItem],
    summary="List quizzes",
)
async def list_quizzes(service: QuizServiceDep) -> list[QuizListItem]:
    """Return every quiz with its identifying fields (`id`, `title`, `description`).

    Questions and options are **not** included — use the detail endpoint for
    that.
    """
    quizzes = await service.list_quizzes()
    return [QuizListItem.model_validate(quiz) for quiz in quizzes]


@router.get(
    "/{quiz_id}",
    response_model=QuizDetail,
    summary="Get a quiz with all its questions and options",
)
async def get_quiz(quiz_id: int, service: QuizServiceDep) -> QuizDetail:
    """Return a quiz with every question and option.

    Correct answers (`is_correct`) and per-question `explanation` fields are
    intentionally excluded — they're revealed only through attempt submission
    and attempt detail.

    Returns `404 quiz_not_found` if the id doesn't exist.
    """
    quiz = await service.get_quiz(quiz_id)
    return QuizDetail.model_validate(quiz)


@router.post(
    "",
    response_model=QuizDetail,
    status_code=status.HTTP_201_CREATED,
    summary="Create a quiz with its full question tree",
)
async def create_quiz(data: QuizCreate, service: QuizServiceDep) -> QuizDetail:
    """Create a quiz, its questions, and their options in a single request.

    The service enforces **exactly one correct option per question** — otherwise
    the request is rejected with `422 invalid_quiz_structure`.

    The response hides `is_correct` and `explanation`, matching the shape of
    the detail endpoint.
    """
    quiz = await service.create_quiz(data)
    return QuizDetail.model_validate(quiz)
