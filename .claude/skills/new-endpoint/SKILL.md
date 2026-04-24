---
name: new-endpoint
description: Scaffold a new QuizApp API endpoint with controller + service + repository + Pydantic schemas + test. Trigger when the user asks to "add", "create", or "scaffold" an endpoint.
---

# new-endpoint

Scaffold a new API endpoint following QuizApp's architecture: Controller → Service → Repository.

## Files to produce

For feature `<feature>` and endpoint `<name>`:

1. **Schemas** — `app/<feature>/schemas.py`: `<Name>Create`, `<Name>Read` (or `<Name>Out`) as needed.
2. **Repository** — `app/<feature>/repository.py`: async method, returns domain objects, no business logic.
3. **Service** — `app/<feature>/service.py`: async method, raises `DomainError` subclasses on business-rule violations.
4. **Controller** — `app/<feature>/controller.py`: registers on the feature's `APIRouter`, wires service via `Depends`, declares `response_model`.
5. **Tests**:
   - Unit: `tests/unit/<feature>/test_<name>_service.py` (mock the repository).
   - Integration: `tests/integration/<feature>/test_<name>_controller.py` (httpx.AsyncClient + real Postgres test DB).
6. **Router registration** — in `app/main.py` if first endpoint of the feature.

## Conventions

- All code in English, minimal comments.
- Type-hint every signature; `async def` throughout.
- Validate at the controller via Pydantic; services assume valid input.
- All endpoints under `/api/v1/...`.

Reference: `CLAUDE.md`.
