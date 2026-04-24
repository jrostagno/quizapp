from unittest.mock import AsyncMock

import pytest

from app.core.errors import InvalidQuizStructureError, QuizNotFoundError
from app.quizzes.models import Quiz
from app.quizzes.schemas import OptionCreate, QuestionCreate, QuizCreate
from app.quizzes.service import QuizService


def _make_service() -> tuple[QuizService, AsyncMock, AsyncMock]:
    repository = AsyncMock()
    session = AsyncMock()
    return QuizService(repository, session), repository, session


def _valid_payload() -> QuizCreate:
    return QuizCreate(
        title="Agent Fundamentals",
        description="Basics of AI agents.",
        questions=[
            QuestionCreate(
                body="What is an agent?",
                explanation="An agent acts on behalf of a user.",
                options=[
                    OptionCreate(body="A program", is_correct=True),
                    OptionCreate(body="A fruit", is_correct=False),
                ],
            )
        ],
    )


async def test_get_quiz_raises_not_found_when_missing() -> None:
    service, repository, _ = _make_service()
    repository.get_by_id.return_value = None

    with pytest.raises(QuizNotFoundError) as exc_info:
        await service.get_quiz(999)

    assert exc_info.value.details == {"quiz_id": 999}


async def test_list_quizzes_delegates_to_repository() -> None:
    service, repository, _ = _make_service()
    expected = [Quiz(id=1, title="Q", description="D")]
    repository.list_all.return_value = expected

    result = await service.list_quizzes()

    assert result == expected
    repository.list_all.assert_awaited_once()


async def test_create_quiz_rejects_question_with_zero_correct_options() -> None:
    service, _, _ = _make_service()
    payload = QuizCreate(
        title="Bad Quiz",
        description="d",
        questions=[
            QuestionCreate(
                body="Q?",
                explanation="E",
                options=[
                    OptionCreate(body="A", is_correct=False),
                    OptionCreate(body="B", is_correct=False),
                ],
            )
        ],
    )

    with pytest.raises(InvalidQuizStructureError) as exc_info:
        await service.create_quiz(payload)

    assert exc_info.value.details == {"question_index": 1, "correct_count": 0}


async def test_create_quiz_rejects_question_with_multiple_correct_options() -> None:
    service, _, _ = _make_service()
    payload = QuizCreate(
        title="Bad Quiz",
        description="d",
        questions=[
            QuestionCreate(
                body="Q?",
                explanation="E",
                options=[
                    OptionCreate(body="A", is_correct=True),
                    OptionCreate(body="B", is_correct=True),
                ],
            )
        ],
    )

    with pytest.raises(InvalidQuizStructureError) as exc_info:
        await service.create_quiz(payload)

    assert exc_info.value.details["correct_count"] == 2


async def test_create_quiz_persists_and_returns_reloaded_entity() -> None:
    service, repository, session = _make_service()
    payload = _valid_payload()
    reloaded = Quiz(id=42, title=payload.title, description=payload.description)
    repository.get_by_id.return_value = reloaded

    async def _set_id(quiz: Quiz) -> Quiz:
        quiz.id = 42
        return quiz

    repository.add.side_effect = _set_id

    result = await service.create_quiz(payload)

    repository.add.assert_awaited_once()
    session.commit.assert_awaited_once()
    repository.get_by_id.assert_awaited_with(42)
    assert result is reloaded
