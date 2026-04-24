from pydantic import BaseModel, ConfigDict, EmailStr


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: EmailStr


class UserStats(BaseModel):
    user_id: int
    total_attempts: int
    average_percentage: float | None
