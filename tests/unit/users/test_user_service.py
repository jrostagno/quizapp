from unittest.mock import AsyncMock

from app.users.models import User
from app.users.service import UserService


async def test_upsert_by_email_delegates_to_repository() -> None:
    repository = AsyncMock()
    session = AsyncMock()
    expected = User(id=1, name="Alice", email="alice@example.com")
    repository.upsert_by_email.return_value = expected

    service = UserService(repository, session)

    result = await service.upsert_by_email(name="Alice", email="alice@example.com")

    assert result is expected
    repository.upsert_by_email.assert_awaited_once_with(name="Alice", email="alice@example.com")
