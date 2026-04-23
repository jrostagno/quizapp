from fastapi import FastAPI

app = FastAPI(
    title="QuizApp",
    description="RESTful API for AI Development quiz challenges.",
    version="0.1.0",
)


@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    return {"status": "ok"}
