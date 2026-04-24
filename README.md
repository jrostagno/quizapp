# QuizApp

RESTful API for AI Development quiz challenges — built with FastAPI, SQLAlchemy,
Postgres, and arq. Submissions are scored synchronously; email notifications
are dispatched asynchronously via a background worker.

## Stack

- Python 3.12, FastAPI (fully async), Pydantic v2 + pydantic-settings
- SQLAlchemy 2.x async + asyncpg, Alembic migrations
- PostgreSQL 16 (Docker), Redis 7 (Docker)
- arq — async task queue backed by Redis
- Pytest + pytest-asyncio, httpx.AsyncClient
- Ruff (lint + format), uv (package manager)
- FastAPI auto OpenAPI + Swagger UI at `/docs`

See [`CLAUDE.md`](CLAUDE.md) for the full architecture reference.

## Running everything in Docker (recommended)

```bash
cp .env.example .env          # tweak values if needed
docker compose up -d --build  # brings up postgres (dev + test), redis, app, worker
```

- API: <http://localhost:8000>
- Swagger UI: <http://localhost:8000/docs>
- Health: <http://localhost:8000/health>

`docker compose logs -f app worker` streams the application and worker logs.
`docker compose down` stops everything; add `-v` to drop the persistent
Postgres volume.

Inside the `app` container, `alembic upgrade head` runs on startup, so the
schema is in sync on every boot.

### Seeding sample data

```bash
docker compose exec app python -m scripts.seed
```

Two quizzes ("Agent Fundamentals", "Prompt Engineering Basics") with five
questions each. Idempotent — re-running skips existing titles.

## Running locally (without the app in Docker)

You can run the API on your host while Postgres + Redis stay in Docker:

```bash
uv sync
cp .env.example .env
docker compose up -d postgres-dev postgres-test redis --wait
uv run alembic upgrade head
uv run python -m scripts.seed        # optional
uv run uvicorn app.main:app --reload # starts on http://localhost:8000
```

And the worker in another terminal:

```bash
uv run arq app.notifications.worker.WorkerSettings
```

## Endpoints

All endpoints live under `/api/v1/...`.

| Method | Path                              | Purpose                                                |
|--------|-----------------------------------|--------------------------------------------------------|
| GET    | `/quizzes`                        | List quizzes (id, title, description)                  |
| GET    | `/quizzes/{id}`                   | Quiz detail with questions + options (no correct answers) |
| POST   | `/quizzes`                        | Create a quiz with its full question tree              |
| POST   | `/attempts`                       | Start an attempt (upserts the user by email)           |
| POST   | `/attempts/{id}/submit`           | Submit answers; returns score + feedback + breakdown   |
| GET    | `/attempts/{id}`                  | Attempt detail with per-question breakdown             |
| GET    | `/users/{id}/attempts`            | List a user's attempts (newest first)                  |
| GET    | `/users/{id}/stats`               | `{total_attempts, average_percentage}`                 |
| GET    | `/health`                         | Liveness probe                                         |

Errors follow a single envelope:

```json
{"error": {"code": "quiz_not_found", "message": "...", "details": {...}}}
```

## Architecture

```
┌───────────────────────────────────────────────────────────┐
│  FastAPI                                                  │
│    ├─ quizzes   →  service  →  repository  →  Postgres    │
│    ├─ attempts  →  service  →  repository  →  Postgres    │
│    │                     ↓                                │
│    │              notifications.service                   │
│    │                     ↓                                │
│    │              enqueue → Redis (arq)                   │
│    └─ users     →  service  →  repository  →  Postgres    │
└───────────────────────────────────────────────────────────┘
                                    ↓
                     ┌──────────────────────────┐
                     │  arq worker (separate)   │
                     │  consumes → send email   │
                     │  updates  → Notification │
                     └──────────────────────────┘
```

- **Controller → Service → Repository** per feature. Controllers only handle
  HTTP shape; services hold business logic; repositories wrap SQLAlchemy.
- **Async end-to-end**: `async def` endpoints, `AsyncSession`, `httpx.AsyncClient`
  in integration tests.
- **Submission never fails on broker outage**: if Redis is down, the
  notification row is marked `failed_to_enqueue` and the `POST /submit`
  response still returns 200.
- **Rich text** in question bodies, options, and explanations is Markdown.

## Running the tests

```bash
uv run pytest                         # full suite (79 tests) in ~1s
uv run pytest tests/unit              # unit only (~0.2s)
uv run pytest tests/integration       # integration (uses postgres-test + redis)
uv run ruff check . && uv run ruff format --check .
```

- Unit tests use `AsyncMock` against the service/repository boundary.
- Integration tests spin a session-scoped `test_engine` against the
  `postgres-test` container (port 5433), clean up with `TRUNCATE … RESTART
  IDENTITY CASCADE` between tests, and flush Redis between tests so arq
  job ids stay clean after the id sequence is reset.

## Pre-commit

A local git hook at `.git/hooks/pre-commit` runs `ruff check` + `ruff format
--check` + `pytest` and blocks the commit on any failure. If you've cloned
fresh, copy it into place or install from the repo — the Python `pre-commit`
framework itself is deferred.

## Project layout

```
app/
  quizzes/        controller · service · repository · models · schemas
  attempts/       same + scoring.py (pure helpers)
  users/          same (no public controller, only per-user progress routes)
  notifications/  same + worker.py (arq WorkerSettings) + email.py (MockEmailSender)
  core/           config · deps · errors · logging
  db/             base · session
alembic/          async migrations
scripts/seed.py   idempotent seed
tests/            unit/ + integration/
.claude/          Skills, hooks, subagent, settings (Claude Code)
docker-compose.yml + Dockerfile + .dockerignore
```
