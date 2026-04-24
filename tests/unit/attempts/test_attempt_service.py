from unittest.mock import AsyncMock, MagicMock

import pytest

from app.attempts.models import Attempt
from app.attempts.schemas import AnswerSubmission, AttemptStartRequest, AttemptSubmitRequest
from app.attempts.service import AttemptService
from app.core.errors import (
    AttemptAlreadySubmittedError,
    AttemptNotFoundError,
    InvalidAnswerSubmissionError,
    QuizNotFoundError,
)
from app.quizzes.models import Option, Question, Quiz
from app.users.models import User


def _make_service() -> tuple[AttemptService, AsyncMock, AsyncMock, AsyncMock, AsyncMock, AsyncMock]:
    repository = AsyncMock()
    repository.add_answers = MagicMock()  # add_answers is sync
    user_service = AsyncMock()
    quiz_service = AsyncMock()
    notification_service = AsyncMock()
    session = AsyncMock()
    service = AttemptService(repository, user_service, quiz_service, notification_service, session)
    return service, repository, user_service, quiz_service, notification_service, session


def _build_quiz() -> tuple[Quiz, Question, Question, Option, Option, Option, Option]:
    q1 = Question(id=10, quiz_id=1, body="Q1?", explanation="exp1", position=1)
    q1_correct = Option(id=100, question_id=10, body="A", is_correct=True, position=1)
    q1_wrong = Option(id=101, question_id=10, body="B", is_correct=False, position=2)
    q1.options = [q1_correct, q1_wrong]

    q2 = Question(id=20, quiz_id=1, body="Q2?", explanation="exp2", position=2)
    q2_correct = Option(id=200, question_id=20, body="X", is_correct=True, position=1)
    q2_wrong = Option(id=201, question_id=20, body="Y", is_correct=False, position=2)
    q2.options = [q2_correct, q2_wrong]

    quiz = Quiz(id=1, title="T", description="D")
    quiz.questions = [q1, q2]
    return quiz, q1, q2, q1_correct, q1_wrong, q2_correct, q2_wrong


async def test_start_attempt_creates_attempt_and_returns_entities() -> None:
    service, repository, user_service, quiz_service, _, session = _make_service()
    user = User(id=7, name="Alice", email="alice@example.com")
    quiz = Quiz(id=3, title="Agents", description="d")
    quiz_service.get_quiz.return_value = quiz
    user_service.upsert_by_email.return_value = user

    async def _set_id(attempt: Attempt) -> Attempt:
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
    service, _, user_service, quiz_service, _, _ = _make_service()
    quiz_service.get_quiz.side_effect = QuizNotFoundError(999)

    request = AttemptStartRequest(name="Alice", email="alice@example.com", quiz_id=999)

    with pytest.raises(QuizNotFoundError):
        await service.start_attempt(request)

    user_service.upsert_by_email.assert_not_awaited()


async def test_submit_attempt_not_found() -> None:
    service, repository, *_ = _make_service()
    repository.get_with_quiz.return_value = None

    request = AttemptSubmitRequest(answers=[AnswerSubmission(question_id=1, option_id=1)])

    with pytest.raises(AttemptNotFoundError):
        await service.submit_attempt(77, request)


async def test_submit_attempt_already_submitted() -> None:
    from datetime import UTC, datetime

    service, repository, *_ = _make_service()
    quiz, *_ = _build_quiz()
    attempt = Attempt(id=5, user_id=1, quiz_id=1, submitted_at=datetime.now(UTC))
    attempt.quiz = quiz
    repository.get_with_quiz.return_value = attempt

    request = AttemptSubmitRequest(answers=[AnswerSubmission(question_id=10, option_id=100)])

    with pytest.raises(AttemptAlreadySubmittedError):
        await service.submit_attempt(5, request)


async def test_submit_attempt_rejects_duplicate_question_ids() -> None:
    service, repository, *_ = _make_service()
    quiz, _, _, q1_correct, q1_wrong, *_ = _build_quiz()
    attempt = Attempt(id=5, user_id=1, quiz_id=1, submitted_at=None)
    attempt.quiz = quiz
    repository.get_with_quiz.return_value = attempt

    request = AttemptSubmitRequest(
        answers=[
            AnswerSubmission(question_id=10, option_id=q1_correct.id),
            AnswerSubmission(question_id=10, option_id=q1_wrong.id),
        ]
    )

    with pytest.raises(InvalidAnswerSubmissionError):
        await service.submit_attempt(5, request)


async def test_submit_attempt_rejects_missing_questions() -> None:
    service, repository, *_ = _make_service()
    quiz, q1, _, q1_correct, *_ = _build_quiz()
    attempt = Attempt(id=5, user_id=1, quiz_id=1, submitted_at=None)
    attempt.quiz = quiz
    repository.get_with_quiz.return_value = attempt

    request = AttemptSubmitRequest(
        answers=[AnswerSubmission(question_id=q1.id, option_id=q1_correct.id)]
    )

    with pytest.raises(InvalidAnswerSubmissionError) as exc_info:
        await service.submit_attempt(5, request)
    assert exc_info.value.details["missing"] == [20]


async def test_submit_attempt_rejects_option_from_other_question() -> None:
    service, repository, *_ = _make_service()
    quiz, q1, q2, q1_correct, _, q2_correct, _ = _build_quiz()
    attempt = Attempt(id=5, user_id=1, quiz_id=1, submitted_at=None)
    attempt.quiz = quiz
    repository.get_with_quiz.return_value = attempt

    request = AttemptSubmitRequest(
        answers=[
            AnswerSubmission(question_id=q1.id, option_id=q2_correct.id),
            AnswerSubmission(question_id=q2.id, option_id=q2_correct.id),
        ]
    )

    with pytest.raises(InvalidAnswerSubmissionError):
        await service.submit_attempt(5, request)


async def test_submit_attempt_all_correct_returns_full_score() -> None:
    service, repository, _, _, notification_service, session = _make_service()
    quiz, q1, q2, q1_correct, _, q2_correct, _ = _build_quiz()
    attempt = Attempt(id=5, user_id=1, quiz_id=1, submitted_at=None)
    attempt.quiz = quiz
    repository.get_with_quiz.return_value = attempt

    request = AttemptSubmitRequest(
        answers=[
            AnswerSubmission(question_id=q1.id, option_id=q1_correct.id),
            AnswerSubmission(question_id=q2.id, option_id=q2_correct.id),
        ]
    )

    result = await service.submit_attempt(5, request)

    assert result.attempt_id == 5
    assert result.score == 2
    assert result.total == 2
    assert result.percentage == 100.0
    assert "Great job" in result.feedback
    assert len(result.questions) == 2
    assert all(q.is_correct for q in result.questions)

    # Attempt updated in memory
    assert attempt.submitted_at is not None
    assert attempt.score == 2
    assert attempt.percentage == 100.0

    # Side effects fired
    notification_service.queue_for_attempt.assert_awaited_once_with(5)
    session.commit.assert_awaited_once()


async def test_submit_attempt_partial_score_and_tier() -> None:
    service, repository, *_ = _make_service()
    quiz, q1, q2, q1_correct, q1_wrong, _, q2_wrong = _build_quiz()
    attempt = Attempt(id=5, user_id=1, quiz_id=1, submitted_at=None)
    attempt.quiz = quiz
    repository.get_with_quiz.return_value = attempt

    request = AttemptSubmitRequest(
        answers=[
            AnswerSubmission(question_id=q1.id, option_id=q1_correct.id),
            AnswerSubmission(question_id=q2.id, option_id=q2_wrong.id),
        ]
    )

    result = await service.submit_attempt(5, request)

    assert result.score == 1
    assert result.percentage == 50.0
    assert "Keep going" in result.feedback
