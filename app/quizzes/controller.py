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


@router.get("", response_model=list[QuizListItem])
async def list_quizzes(service: QuizServiceDep) -> list[QuizListItem]:
    quizzes = await service.list_quizzes()
    return [QuizListItem.model_validate(quiz) for quiz in quizzes]


@router.get("/{quiz_id}", response_model=QuizDetail)
async def get_quiz(quiz_id: int, service: QuizServiceDep) -> QuizDetail:
    quiz = await service.get_quiz(quiz_id)
    return QuizDetail.model_validate(quiz)


@router.post("", response_model=QuizDetail, status_code=status.HTTP_201_CREATED)
async def create_quiz(data: QuizCreate, service: QuizServiceDep) -> QuizDetail:
    quiz = await service.create_quiz(data)
    return QuizDetail.model_validate(quiz)
