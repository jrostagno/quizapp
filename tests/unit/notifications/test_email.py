from datetime import UTC, datetime

from app.notifications.email import EmailPayload, MockEmailSender, build_payload


def _payload() -> EmailPayload:
    return build_payload(
        user_name="Alice",
        user_email="alice@example.com",
        quiz_title="Agent Fundamentals",
        score=4,
        total=5,
        percentage=80.0,
        feedback="Great job! You're getting there!",
        submitted_at=datetime(2026, 4, 23, 12, 0, tzinfo=UTC),
    )


def test_build_payload_contains_all_required_fields() -> None:
    payload = _payload()

    assert payload.to == "alice@example.com"
    assert "Agent Fundamentals" in payload.subject
    assert "Alice" in payload.body
    assert "4/5" in payload.body
    assert "80.0" in payload.body
    assert "Great job" in payload.body
    assert "2026-04-23" in payload.body


async def test_mock_sender_send_does_not_raise() -> None:
    sender = MockEmailSender()
    await sender.send(_payload())
