from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.quizzes.schemas import QuizDetail
from app.users.schemas import UserRead


class AttemptStartRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr
    quiz_id: int = Field(..., ge=1)


class AttemptStartResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    started_at: datetime
    user: UserRead
    quiz: QuizDetail


class AnswerSubmission(BaseModel):
    question_id: int = Field(..., ge=1)
    option_id: int = Field(..., ge=1)


class AttemptSubmitRequest(BaseModel):
    answers: list[AnswerSubmission] = Field(..., min_length=1)


class QuestionResult(BaseModel):
    question_id: int
    selected_option_id: int
    correct_option_id: int
    is_correct: bool
    explanation: str


class AttemptResult(BaseModel):
    attempt_id: int
    submitted_at: datetime
    score: int
    total: int
    percentage: float
    feedback: str
    questions: list[QuestionResult]
