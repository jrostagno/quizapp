from fastapi import FastAPI

from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging
from app.quizzes.controller import router as quizzes_router

API_V1_PREFIX = "/api/v1"


def create_app() -> FastAPI:
    configure_logging()

    app = FastAPI(
        title="QuizApp",
        description="RESTful API for AI Development quiz challenges.",
        version="0.1.0",
    )
    register_exception_handlers(app)

    app.include_router(quizzes_router, prefix=API_V1_PREFIX)

    @app.get("/health", tags=["health"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
