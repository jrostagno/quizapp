from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class DomainError(Exception):
    code: str = "domain_error"
    status_code: int = 400

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class QuizNotFoundError(DomainError):
    code = "quiz_not_found"
    status_code = 404

    def __init__(self, quiz_id: int) -> None:
        super().__init__(
            f"Quiz with id {quiz_id} was not found.",
            details={"quiz_id": quiz_id},
        )


class InvalidQuizStructureError(DomainError):
    code = "invalid_quiz_structure"
    status_code = 422


class AttemptNotFoundError(DomainError):
    code = "attempt_not_found"
    status_code = 404

    def __init__(self, attempt_id: int) -> None:
        super().__init__(
            f"Attempt with id {attempt_id} was not found.",
            details={"attempt_id": attempt_id},
        )


class AttemptAlreadySubmittedError(DomainError):
    code = "attempt_already_submitted"
    status_code = 409

    def __init__(self, attempt_id: int) -> None:
        super().__init__(
            f"Attempt {attempt_id} has already been submitted.",
            details={"attempt_id": attempt_id},
        )


class InvalidAnswerSubmissionError(DomainError):
    code = "invalid_answer_submission"
    status_code = 422


class UserNotFoundError(DomainError):
    code = "user_not_found"
    status_code = 404

    def __init__(self, user_id: int) -> None:
        super().__init__(
            f"User with id {user_id} was not found.",
            details={"user_id": user_id},
        )


def _domain_error_handler(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, DomainError)
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
            },
        },
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(DomainError, _domain_error_handler)
