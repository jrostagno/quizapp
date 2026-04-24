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
