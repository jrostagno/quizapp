import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from arq import create_pool
from arq.connections import RedisSettings
from fastapi import FastAPI

from app.attempts.controller import router as attempts_router
from app.core.config import get_settings
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging
from app.quizzes.controller import router as quizzes_router
from app.users.controller import router as users_router

API_V1_PREFIX = "/api/v1"

logger = logging.getLogger(__name__)


APP_DESCRIPTION = """
RESTful API for AI Development quiz challenges.

## What it does

- Create quizzes with Markdown content (questions, options, explanations).
- Start quiz attempts — users are upserted by email on the first attempt.
- Submit answers; receive a score, a feedback message, and a per-question
  breakdown with correctness and explanations.
- Queue an asynchronous email notification (arq + Redis). Submission does
  not fail if the broker is unavailable.
- List a user's attempts and aggregate stats (total attempts, average
  percentage over submitted attempts).

## Conventions

- Every endpoint is mounted under `/api/v1/...`.
- Errors follow a consistent envelope: `{"error": {"code", "message", "details"}}`.
- Correct answers and explanations are only exposed via attempt submission
  and attempt detail endpoints, never on the quiz GETs.
- Question and option bodies, plus explanations, are stored as Markdown.
""".strip()


TAGS_METADATA = [
    {
        "name": "health",
        "description": "Liveness probe.",
    },
    {
        "name": "quizzes",
        "description": (
            "Create and retrieve quizzes. Correct answers and explanations are "
            "**never** exposed here."
        ),
    },
    {
        "name": "attempts",
        "description": (
            "Start a quiz attempt, submit answers for scoring, and fetch the full "
            "per-question breakdown. Submitting also queues an asynchronous email "
            "notification."
        ),
    },
    {
        "name": "users",
        "description": (
            "Per-user progress and aggregate stats. Users are never created here "
            "directly — the first `POST /api/v1/attempts` with a given email "
            "creates the user."
        ),
    },
]


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    settings = get_settings()
    try:
        app.state.arq_pool = await create_pool(RedisSettings.from_dsn(settings.redis_url))
    except Exception as exc:
        logger.warning(
            "arq pool not available — notifications will be marked failed_to_enqueue",
            extra={"error": str(exc)},
        )
        app.state.arq_pool = None

    try:
        yield
    finally:
        pool = getattr(app.state, "arq_pool", None)
        if pool is not None:
            await pool.aclose()


def create_app() -> FastAPI:
    configure_logging()

    app = FastAPI(
        title="QuizApp",
        description=APP_DESCRIPTION,
        version="0.1.0",
        openapi_tags=TAGS_METADATA,
        lifespan=lifespan,
    )
    register_exception_handlers(app)

    app.include_router(quizzes_router, prefix=API_V1_PREFIX)
    app.include_router(attempts_router, prefix=API_V1_PREFIX)
    app.include_router(users_router, prefix=API_V1_PREFIX)

    @app.get(
        "/health",
        tags=["health"],
        summary="Liveness probe",
    )
    async def health() -> dict[str, str]:
        """Return a static `{"status": "ok"}` payload when the process is running."""
        return {"status": "ok"}

    return app


app = create_app()
