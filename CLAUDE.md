# QuizApp

## Project Overview

The AI Development Quiz App is an educational product designed to help users test and reinforce their understanding of AI software development concepts, including agent design, prompt engineering, and workflow automation. This project is a RESTful API backend that manages quizzes, tracks user attempts, calculates scores, and sends asynchronous result notifications.

## Project Status

Practice run for an FSL coding challenge. The scope is deliberately limited to what the challenge requires — no authentication, rate limiting, caching, or production hardening. A final screen-recorded submission will be produced later; the environment and agent setup must be ready **before** recording starts.

## Tech Stack

| Concern                    | Choice                                                            |
|----------------------------|-------------------------------------------------------------------|
| Language                   | Python 3.12+                                                      |
| Web framework              | FastAPI (fully async)                                             |
| Validation & schemas       | Pydantic v2                                                       |
| Config loader              | `pydantic-settings`                                               |
| ORM                        | SQLAlchemy 2.x (async)                                            |
| Database driver            | `asyncpg`                                                         |
| Database                   | PostgreSQL (in Docker)                                            |
| Migrations                 | Alembic                                                           |
| Async task queue           | `arq` (Redis-backed)                                              |
| Message broker             | Redis (in Docker)                                                 |
| Testing                    | Pytest + `pytest-asyncio`                                         |
| HTTP test client           | `httpx.AsyncClient` + `ASGITransport`                             |
| Test database              | Postgres in a dedicated Docker container (same engine as dev)     |
| Linter + formatter         | Ruff (lint + format)                                              |
| Type checker               | None (no mypy, no pyright)                                        |
| Package manager            | `uv`                                                              |
| API documentation          | FastAPI-generated OpenAPI + Swagger UI at `/docs`                 |

## Architecture

### Layering (per feature)

```
Controller  →  Service  →  Repository  →  Database
(APIRouter)    (business)   (SQLAlchemy)
```

- **Controller** — defines the HTTP endpoints for a feature. Internally it is a FastAPI `APIRouter`, but across this codebase we **call it a controller** and the file is named `controller.py`. Validates input via Pydantic schemas; translates domain exceptions to HTTP responses via global handlers.
- **Service** — business logic. Pure Python, no HTTP and no ORM leaking. Orchestrates repositories, enforces invariants, raises domain exceptions.
- **Repository** — persistence boundary. Wraps SQLAlchemy, returns domain objects (not raw rows). No business logic here.

### Folder structure (by feature / domain)

```
app/
  quizzes/
    controller.py
    service.py
    repository.py
    models.py         # SQLAlchemy ORM models
    schemas.py        # Pydantic request/response schemas
  attempts/
    controller.py
    service.py
    repository.py
    models.py
    schemas.py
  users/
    controller.py
    service.py
    repository.py
    models.py
    schemas.py
  notifications/
    service.py
    repository.py
    models.py
    schemas.py
    worker.py         # arq worker tasks
  core/
    config.py         # pydantic-settings Settings
    errors.py         # DomainError + subclasses, FastAPI handlers
    deps.py           # FastAPI Depends() wiring (session, services, repos)
    logging.py        # stdlib logging config
  db/
    base.py           # Declarative base
    session.py        # async engine + async sessionmaker
  main.py             # FastAPI app factory, controller registration
alembic/              # migrations
scripts/
  seed.py             # idempotent seed script
tests/
  unit/
  integration/
  conftest.py
docker-compose.yml    # Postgres + Redis (added in the setup stage)
Dockerfile            # app containerization (end of project)
pyproject.toml
.env
.env.example
```

### API versioning

All endpoints are mounted under `/api/v1/...`. Controllers are registered in `main.py` with this prefix.

### Async model

Fully async end-to-end: `async def` endpoints, `AsyncSession`, async repositories, async services where I/O is involved. The session is injected into services via FastAPI `Depends()`.

### Dependency injection

FastAPI's native `Depends()` is the DI mechanism. Session factories, repositories, and services are wired in `app/core/deps.py`.

### Error handling

- Domain exceptions inherit from a base `DomainError` (in `core/errors.py`) — e.g. `QuizNotFoundError`, `AttemptAlreadySubmittedError`, `UserNotFoundError`.
- Global FastAPI exception handlers map each exception type to an HTTP status code and a consistent JSON error body:

  ```json
  { "error": { "code": "quiz_not_found", "message": "...", "details": {} } }
  ```

- Pydantic validation errors are handled by FastAPI's built-in 422 handler (optionally customized for shape).
- Services assume input has already been validated at the controller boundary; they raise domain exceptions only for business-rule violations.

### Async notification dispatch (arq + Redis)

- On quiz submission, the attempt service: computes the result, persists the attempt and answers, creates a `notifications` row with `status = queued`, and **enqueues an `arq` job**.
- The `arq` worker runs as a separate process; it consumes the job, simulates sending the email (mock), and updates the notification row to `sent` or `failed`. `arq` provides retries natively.
- If enqueueing fails (Redis down, etc.), the submission **still succeeds**. The notification row is marked `failed_to_enqueue` and logged. The API response is unaffected.
- The email payload includes: user name, email, quiz title, score (correct / total), percentage, feedback message, completion timestamp.

### Domain rules

- **Questions** have multiple options and **exactly one correct answer**.
- **Rich text** content (question and option bodies, explanations) is stored as **Markdown**; rendering is the client's concern.
- **Users** are created via **upsert-by-email** in the `start attempt` flow: the request body carries `{ name, email }`; if no user exists with that email, one is created; otherwise the existing user is reused.
- **Feedback tiers**, based on percentage score:
  - `>= 80%` → encouraging message
  - `60–79%` → motivational message
  - `< 60%` → improvement encouragement

### Seeds

A plain Python script (`scripts/seed.py`), idempotent, inserts at least 2 quizzes with 5+ questions each. Run via `uv run python scripts/seed.py`.

## Language Conventions

- **Code** (identifiers, function names, class names, file names): English
- **Comments**: English, minimal — only for non-obvious "why", never for "what"
- **Documentation** (this file, README, API docs): English
- **Commit messages and PR descriptions**: English
- **Conversational language with the agent**: Spanish (user preference); all written artifacts remain English

## Coding Conventions

- Idiomatic Python 3.12, modern FastAPI and SQLAlchemy 2.x async style.
- Type hints on every function signature (enforced by style and Ruff's rules, not by a type checker).
- Pydantic schemas live alongside the feature; distinguish `*Create`, `*Update`, `*Read` (or `*Out`) variants.
- SQLAlchemy ORM models use the modern `Mapped[...]` + `mapped_column(...)` style.
- Keep comments minimal; well-named identifiers are the documentation.
- No dead code, commented-out code, or stale TODOs after a stage closes.
- Services assume input is already validated; they raise domain exceptions for business-rule violations.

## Testing Strategy

- **No TDD.** Tests are written alongside or after implementation for each stage.
- **Unit tests** cover business logic with no I/O: scoring, feedback tier selection, notification payload construction. Repositories are mocked at the service boundary.
- **Integration tests** exercise the full HTTP → service → real Postgres stack using `httpx.AsyncClient` against the FastAPI app. The test Postgres runs in a **dedicated Docker container**, isolated from the dev DB but using the same image version.
- **Email service is mocked** in all tests (challenge requirement).
- **No strict coverage target.** Cover business logic confidently; do not chase numbers.
- **Fixtures** are handwritten in `conftest.py`; no `factory_boy` / `polyfactory`.

## Git Workflow

- **Hosting**: GitHub (repo created via GitHub MCP).
- **Branching**: `main` + short-lived feature branches per checklist stage.
- **Commits**: [Conventional Commits](https://www.conventionalcommits.org/) — `feat:`, `fix:`, `chore:`, `docs:`, `test:`, `refactor:`.
- **Confirmation**: the agent asks for explicit confirmation before every commit.
- **Push cadence**: stage by stage, after the checklist item is verified.
- **Never bypass hooks** with `--no-verify`. If a hook fails, fix the root cause.

## Pre-commit Validation

Two cooperating layers; both run `ruff check` + `ruff format --check` + `pytest` and block on any failure.

1. **Git hook** — a plain shell script at `.git/hooks/pre-commit` installed manually during setup. This is the authoritative gate for `git commit` (including commits from outside the agent). The Python **`pre-commit` framework is deferred** for a later iteration.
2. **Claude Code hook** — configured in `.claude/settings.json` as a PreToolUse hook on Bash `git commit`. This protects agent-initiated commits with the same checks.

## Environment

- `.env` — local only, git-ignored, real values (DB URL, Redis URL, log level).
- `.env.example` — committed, lists every required variable with placeholders and a short comment.
- Config is loaded via `pydantic-settings` in `core/config.py`.

## Infrastructure

- **PostgreSQL (dev)** runs in a Docker container.
- **PostgreSQL (test)** runs in a separate Docker container, same image version.
- **Redis** runs in a Docker container (required by `arq`).
- All three services are orchestrated via `docker-compose.yml`, added during the setup stage.
- **The application itself is dockerized at the end of the project** (Dockerfile + a compose service), not during development.

## Logging

- Python stdlib `logging` with a JSON formatter.
- Level configurable via `LOG_LEVEL` env var (default `INFO`).
- No external observability stack (no Sentry, no OpenTelemetry).

## Definition of Done (per checklist stage)

- [ ] All tests pass (unit + integration where applicable)
- [ ] `ruff check` and `ruff format --check` pass
- [ ] Swagger / OpenAPI reflects new or changed endpoints
- [ ] Manual smoke test via Swagger UI or `curl`
- [ ] Commit(s) created after explicit user confirmation

## Build / Test / Run Commands

All commands run through `uv`.

```bash
# dependencies
uv sync                              # install from lockfile
uv add <pkg>                         # add a runtime dependency
uv add --dev <pkg>                   # add a dev dependency

# app
uv run uvicorn app.main:app --reload

# quality
uv run ruff check .
uv run ruff format .
uv run ruff format --check .

# tests
uv run pytest
uv run pytest tests/unit
uv run pytest tests/integration

# database
uv run alembic revision --autogenerate -m "message"
uv run alembic upgrade head
uv run python scripts/seed.py

# async worker
uv run arq app.notifications.worker.WorkerSettings
```

## Scope and Non-Goals

**In scope** (challenge requirements):

- RESTful API: quizzes, attempts, scoring, user progress, stats
- Async email notification on quiz completion (`arq` + Redis, email mocked)
- Postgres persistence with Alembic migrations
- Interactive API documentation (FastAPI's Swagger UI at `/docs`)
- Seed data: 2+ quizzes, 5+ questions each
- Unit + integration tests on scoring, feedback calculation, async messaging
- Required Claude Code features: CLAUDE.md, Skills, Hooks, MCP, Subagents

**Out of scope (explicit non-goals):**

- Authentication / authorization
- Rate limiting / throttling
- Caching layer
- Production deployment / CI/CD pipelines
- Observability stack (metrics, tracing)
- Real email delivery
- ADRs (decisions live here and in engram memory)
- Type checking (mypy / pyright)
- `pre-commit` Python framework (deferred)

## Claude Code Configuration

### Skills

Defined under `.claude/skills/`:

- **`new-endpoint`** — scaffold a new API endpoint: controller + service + repository + Pydantic schemas + SQLAlchemy model (when needed) + test + OpenAPI tags.
- **`new-migration`** — create a new Alembic migration (`alembic revision --autogenerate`).
- **`seed-data`** — run or extend the Python seed script.
- **`run-checks`** — execute `ruff check`, `ruff format --check`, and `pytest` as a single gate (equivalent to the pre-commit hook).

### Hooks

Configured in `.claude/settings.json`:

- **Pre-commit (PreToolUse on Bash `git commit`)**: runs `ruff check && ruff format --check && pytest`; blocks the commit on any failure.
- **Session-start**: empty for now; may be extended later.

### MCP Servers

- **GitHub MCP** — create and manage the repo, issues, PRs, pushes.
- **Brave MCP** — web search constrained to official documentation (recording rules forbid Stack Overflow / blogs / forums).
- **Context7 MCP** — fetch up-to-date official docs for libraries used in the project (FastAPI, SQLAlchemy, Pydantic, Alembic, arq).

### Subagents

Defined under `.claude/agents/`:

- **`TestWriter`** — specialized agent for writing unit and integration tests. Runs in isolated context; familiar with this project's testing conventions (pytest, `httpx.AsyncClient`, Postgres test container, handwritten fixtures, no factories).

Additional specialized subagents may be added as needs emerge.

## Collaboration Style

- **Workflow**: planning-driven. Every stage begins with a plan and checklist; execution proceeds stage by stage with review between stages.
- **Verbosity**: medium — concise, with enough context to review decisions.
- **Confirmation gates**: the agent asks before every commit and before any destructive or hard-to-reverse action (DB drop, force push, branch delete, dependency removal).
- **Autonomy within a stage**: the agent may edit files, run tests, and iterate freely on local, reversible work within the current planned stage.
- **Persistent memory (engram)**: active. Decisions, conventions, bug fixes, and non-obvious discoveries are saved across sessions.

## Plan — Next Step

With the stack and architecture locked, the next step is to build the **action plan**: a phased checklist from zero to a working API, roughly scaffolding → tooling → DB & Alembic → core infra → feature-by-feature implementation → async notification → seeds → tests → dockerization. Postgres and Redis containers are brought up in the first stage that actually needs them, not up front.
