from pydantic import BaseModel, ConfigDict, Field

QUIZ_CREATE_EXAMPLE = {
    "title": "LLM Basics",
    "description": "Fundamental concepts about Large Language Models.",
    "questions": [
        {
            "body": "What is an LLM **token**?",
            "explanation": "A token is a sub-word unit the model processes.",
            "options": [
                {"body": "A unit of text like a word or sub-word", "is_correct": True},
                {"body": "A security credential", "is_correct": False},
                {"body": "A unit of money", "is_correct": False},
            ],
        }
    ],
}

QUIZ_DETAIL_EXAMPLE = {
    "id": 1,
    "title": "LLM Basics",
    "description": "Fundamental concepts about Large Language Models.",
    "questions": [
        {
            "id": 10,
            "position": 1,
            "body": "What is an LLM **token**?",
            "options": [
                {"id": 100, "position": 1, "body": "A unit of text like a word or sub-word"},
                {"id": 101, "position": 2, "body": "A security credential"},
                {"id": 102, "position": 3, "body": "A unit of money"},
            ],
        }
    ],
}


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
    model_config = ConfigDict(json_schema_extra={"examples": [QUIZ_CREATE_EXAMPLE]})

    title: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=1)
    questions: list[QuestionCreate] = Field(..., min_length=1)


class QuizListItem(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "id": 1,
                    "title": "LLM Basics",
                    "description": "Fundamental concepts about Large Language Models.",
                }
            ]
        },
    )

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
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={"examples": [QUIZ_DETAIL_EXAMPLE]},
    )

    id: int
    title: str
    description: str
    questions: list[QuestionPublic]
