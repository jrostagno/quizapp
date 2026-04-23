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
uv run uvicorn app.main:app --reload
```

Then open `http://localhost:8000/docs` for the interactive API docs.
