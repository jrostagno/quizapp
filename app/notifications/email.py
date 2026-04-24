import logging
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class EmailPayload:
    to: str
    subject: str
    body: str


def build_payload(
    *,
    user_name: str,
    user_email: str,
    quiz_title: str,
    score: int,
    total: int,
    percentage: float,
    feedback: str,
    submitted_at: datetime,
) -> EmailPayload:
    body = (
        f"Hi {user_name},\n\n"
        f'You completed the quiz "{quiz_title}".\n\n'
        f"Score: {score}/{total} ({percentage}%)\n"
        f"Feedback: {feedback}\n\n"
        f"Completed at: {submitted_at.isoformat()}\n\n"
        f"— QuizApp"
    )
    return EmailPayload(
        to=user_email,
        subject=f"Your QuizApp result: {quiz_title}",
        body=body,
    )


class MockEmailSender:
    async def send(self, payload: EmailPayload) -> None:
        logger.info(
            "mock email sent",
            extra={
                "email_to": payload.to,
                "email_subject": payload.subject,
            },
        )
