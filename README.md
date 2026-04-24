# QuizApp

RESTful API for AI Development quiz challenges — built with FastAPI, SQLAlchemy, and Postgres.

## Stack

- Python 3.12+, FastAPI (async), Pydantic v2
- PostgreSQL (Docker), Redis (Docker)
- SQLAlchemy 2.x async, Alembic, arq
- Pytest, Ruff, uv

See [`CLAUDE.md`](CLAUDE.md) for full architecture and conventions.

## Quickstart

```bash
uv sync
cp .env.example .env
docker compose up -d --wait
uv run alembic upgrade head
uv run python -m scripts.seed  # optional: loads two sample quizzes
uv run uvicorn app.main:app --reload
```

The seed script is idempotent — re-running it skips quizzes that already
exist (matched by title).

Then open `http://localhost:8000/docs` for the interactive API docs.

## Background worker

Quiz submissions enqueue an email notification into Redis. A separate arq worker
consumes the queue, invokes the (mocked) email sender, and updates the
notification row. Run it in a second terminal:

```bash
uv run arq app.notifications.worker.WorkerSettings
```

If Redis or the worker are not available, submissions still succeed — the
notification row is marked `failed_to_enqueue` instead.
