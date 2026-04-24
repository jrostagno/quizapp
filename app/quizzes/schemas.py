from pydantic import BaseModel, ConfigDict, Field


class OptionCreate(BaseModel):
    body: str = Field(..., min_length=1)
    is_correct: bool = False
    position: int | None = Field(default=None, ge=1)


class QuestionCreate(BaseModel):
    body: str = Field(..., min_length=1)
    explanation: str = Field(..., min_length=1)
    position: int | None = Field(default=None, ge=1)
    options: list[OptionCreate] = Field(..., min_length=2)


class QuizCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=1)
    questions: list[QuestionCreate] = Field(..., min_length=1)


class QuizListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str


class OptionPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    position: int
    body: str


class QuestionPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    position: int
    body: str
    options: list[OptionPublic]


class QuizDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str
    questions: list[QuestionPublic]
