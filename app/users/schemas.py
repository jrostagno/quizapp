from pydantic import BaseModel, ConfigDict, EmailStr


class UserRead(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={"examples": [{"id": 3, "name": "Alice", "email": "alice@example.com"}]},
    )

    id: int
    name: str
    email: EmailStr


class UserStats(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"user_id": 3, "total_attempts": 3, "average_percentage": 75.0},
                {"user_id": 3, "total_attempts": 1, "average_percentage": None},
            ]
        }
    )

    user_id: int
    total_attempts: int
    average_percentage: float | None
