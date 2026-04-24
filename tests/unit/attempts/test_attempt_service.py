from unittest.mock import AsyncMock

import pytest

from app.attempts.schemas import AttemptStartRequest
from app.attempts.service import AttemptService
from app.core.errors import QuizNotFoundError
from app.quizzes.models import Quiz
from app.users.models import User


def _make_service() -> tuple[AttemptService, AsyncMock, AsyncMock, AsyncMock, AsyncMock]:
    repository = AsyncMock()
    user_service = AsyncMock()
    quiz_service = AsyncMock()
    session = AsyncMock()
    service = AttemptService(repository, user_service, quiz_service, session)
    return service, repository, user_service, quiz_service, session


async def test_start_attempt_creates_attempt_and_returns_entities() -> None:
    service, repository, user_service, quiz_service, session = _make_service()
    user = User(id=7, name="Alice", email="alice@example.com")
    quiz = Quiz(id=3, title="Agents", description="d")
    quiz_service.get_quiz.return_value = quiz
    user_service.upsert_by_email.return_value = user

    async def _set_id(attempt):
        attempt.id = 42
        return attempt

    repository.add.side_effect = _set_id

    request = AttemptStartRequest(name="Alice", email="alice@example.com", quiz_id=3)
    attempt, returned_user, returned_quiz = await service.start_attempt(request)

    quiz_service.get_quiz.assert_awaited_once_with(3)
    user_service.upsert_by_email.assert_awaited_once_with(name="Alice", email="alice@example.com")
    repository.add.assert_awaited_once()
    session.commit.assert_awaited_once()
    session.refresh.assert_awaited_once_with(attempt)

    assert attempt.id == 42
    assert attempt.user_id == 7
    assert attempt.quiz_id == 3
    assert returned_user is user
    assert returned_quiz is quiz


async def test_start_attempt_propagates_quiz_not_found() -> None:
    service, _, user_service, quiz_service, _ = _make_service()
    quiz_service.get_quiz.side_effect = QuizNotFoundError(999)

    request = AttemptStartRequest(name="Alice", email="alice@example.com", quiz_id=999)

    with pytest.raises(QuizNotFoundError):
        await service.start_attempt(request)

    user_service.upsert_by_email.assert_not_awaited()
