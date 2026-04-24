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
