---
name: new-migration
description: Create a new Alembic migration for QuizApp using autogenerate. Trigger after any SQLAlchemy model change.
---

# new-migration

Create a new Alembic migration after modifying SQLAlchemy models.

## Steps

1. Ensure the Postgres dev container is up.
2. Generate the migration:
   ```bash
   uv run alembic revision --autogenerate -m "<message>"
   ```
3. Review `alembic/versions/<new>.py` — autogenerate misses data-only changes and some enum operations.
4. Apply: `uv run alembic upgrade head`.
5. Verify the schema in Postgres.

## Conventions

- Message in lowercase_snake: `add_users_table`, `add_notification_status_column`.
- One logical change per migration.
- Never edit an applied migration; create a new one.
