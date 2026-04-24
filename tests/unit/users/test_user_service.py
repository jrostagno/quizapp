from unittest.mock import AsyncMock

import pytest

from app.attempts.models import Attempt
from app.core.errors import UserNotFoundError
from app.users.models import User
from app.users.schemas import UserStats
from app.users.service import UserService


def _make_service() -> tuple[UserService, AsyncMock, AsyncMock]:
    repository = AsyncMock()
    attempt_repository = AsyncMock()
    session = AsyncMock()
    return UserService(repository, attempt_repository, session), repository, attempt_repository


async def test_upsert_by_email_delegates_to_repository() -> None:
    service, repository, _ = _make_service()
    expected = User(id=1, name="Alice", email="alice@example.com")
    repository.upsert_by_email.return_value = expected

    result = await service.upsert_by_email(name="Alice", email="alice@example.com")

    assert result is expected
    repository.upsert_by_email.assert_awaited_once_with(name="Alice", email="alice@example.com")


async def test_get_by_id_returns_user() -> None:
    service, repository, _ = _make_service()
    expected = User(id=42, name="Bob", email="bob@example.com")
    repository.get_by_id.return_value = expected

    result = await service.get_by_id(42)

    assert result is expected


async def test_get_by_id_raises_when_missing() -> None:
    service, repository, _ = _make_service()
    repository.get_by_id.return_value = None

    with pytest.raises(UserNotFoundError) as exc_info:
        await service.get_by_id(99)

    assert exc_info.value.details == {"user_id": 99}


async def test_list_attempts_requires_existing_user() -> None:
    service, repository, _ = _make_service()
    repository.get_by_id.return_value = None

    with pytest.raises(UserNotFoundError):
        await service.list_attempts(99)


async def test_list_attempts_delegates_to_attempt_repository() -> None:
    service, repository, attempt_repository = _make_service()
    repository.get_by_id.return_value = User(id=1, name="A", email="a@a.com")
    expected = [Attempt(id=1, user_id=1, quiz_id=1)]
    attempt_repository.list_by_user.return_value = expected

    result = await service.list_attempts(1)

    assert result == expected
    attempt_repository.list_by_user.assert_awaited_once_with(1)


async def test_get_stats_requires_existing_user() -> None:
    service, repository, _ = _make_service()
    repository.get_by_id.return_value = None

    with pytest.raises(UserNotFoundError):
        await service.get_stats(99)


async def test_get_stats_rounds_average_and_returns_values() -> None:
    service, repository, attempt_repository = _make_service()
    repository.get_by_id.return_value = User(id=1, name="A", email="a@a.com")
    attempt_repository.stats_for_user.return_value = (3, 72.3456)

    result = await service.get_stats(1)

    assert result == UserStats(user_id=1, total_attempts=3, average_percentage=72.35)


async def test_get_stats_passes_none_average_when_no_submissions() -> None:
    service, repository, attempt_repository = _make_service()
    repository.get_by_id.return_value = User(id=1, name="A", email="a@a.com")
    attempt_repository.stats_for_user.return_value = (2, None)

    result = await service.get_stats(1)

    assert result == UserStats(user_id=1, total_attempts=2, average_percentage=None)
