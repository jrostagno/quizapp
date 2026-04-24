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

API_V1_PREFIX = "/api/v1"

logger = logging.getLogger(__name__)


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
        description="RESTful API for AI Development quiz challenges.",
        version="0.1.0",
        lifespan=lifespan,
    )
    register_exception_handlers(app)

    app.include_router(quizzes_router, prefix=API_V1_PREFIX)
    app.include_router(attempts_router, prefix=API_V1_PREFIX)

    @app.get("/health", tags=["health"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
