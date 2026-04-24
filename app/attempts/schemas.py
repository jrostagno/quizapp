from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.quizzes.schemas import QUIZ_DETAIL_EXAMPLE, QuizDetail
from app.users.schemas import UserRead


class AttemptStartRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"name": "Alice", "email": "alice@example.com", "quiz_id": 1},
            ]
        }
    )

    name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr
    quiz_id: int = Field(..., ge=1)


class AttemptStartResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "id": 7,
                    "started_at": "2026-04-23T18:30:00+00:00",
                    "user": {"id": 3, "name": "Alice", "email": "alice@example.com"},
                    "quiz": QUIZ_DETAIL_EXAMPLE,
                }
            ]
        },
    )

    id: int
    started_at: datetime
    user: UserRead
    quiz: QuizDetail


class AnswerSubmission(BaseModel):
    question_id: int = Field(..., ge=1)
    option_id: int = Field(..., ge=1)


class AttemptSubmitRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "answers": [
                        {"question_id": 10, "option_id": 100},
                        {"question_id": 20, "option_id": 201},
                    ]
                }
            ]
        }
    )

    answers: list[AnswerSubmission] = Field(..., min_length=1)


class QuestionResult(BaseModel):
    question_id: int
    selected_option_id: int
    correct_option_id: int
    is_correct: bool
    explanation: str


class AttemptResult(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "attempt_id": 7,
                    "submitted_at": "2026-04-23T18:45:00+00:00",
                    "score": 2,
                    "total": 2,
                    "percentage": 100.0,
                    "feedback": "Great job! You're getting there!",
                    "questions": [
                        {
                            "question_id": 10,
                            "selected_option_id": 100,
                            "correct_option_id": 100,
                            "is_correct": True,
                            "explanation": "A token is a sub-word unit the model processes.",
                        }
                    ],
                }
            ]
        }
    )

    attempt_id: int
    submitted_at: datetime
    score: int
    total: int
    percentage: float
    feedback: str
    questions: list[QuestionResult]


class AttemptListItem(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "id": 7,
                    "quiz_id": 1,
                    "quiz_title": "LLM Basics",
                    "started_at": "2026-04-23T18:30:00+00:00",
                    "submitted_at": "2026-04-23T18:45:00+00:00",
                    "score": 2,
                    "percentage": 100.0,
                }
            ]
        }
    )

    id: int
    quiz_id: int
    quiz_title: str
    started_at: datetime
    submitted_at: datetime | None
    score: int | None
    percentage: float | None


class AttemptQuestionDetail(BaseModel):
    question_id: int
    body: str
    position: int
    selected_option_id: int
    correct_option_id: int
    is_correct: bool
    explanation: str


class AttemptDetail(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "id": 7,
                    "user_id": 3,
                    "quiz_id": 1,
                    "quiz_title": "LLM Basics",
                    "started_at": "2026-04-23T18:30:00+00:00",
                    "submitted_at": "2026-04-23T18:45:00+00:00",
                    "score": 2,
                    "total": 2,
                    "percentage": 100.0,
                    "feedback": "Great job! You're getting there!",
                    "questions": [
                        {
                            "question_id": 10,
                            "body": "What is an LLM **token**?",
                            "position": 1,
                            "selected_option_id": 100,
                            "correct_option_id": 100,
                            "is_correct": True,
                            "explanation": "A token is a sub-word unit the model processes.",
                        }
                    ],
                }
            ]
        }
    )

    id: int
    user_id: int
    quiz_id: int
    quiz_title: str
    started_at: datetime
    submitted_at: datetime | None
    score: int | None
    total: int
    percentage: float | None
    feedback: str | None
    questions: list[AttemptQuestionDetail]
