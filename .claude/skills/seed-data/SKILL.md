---
name: seed-data
description: Seed the QuizApp database with sample quizzes and questions. Trigger on "seed", "load seed data", "populate the database".
---

# seed-data

Run the idempotent seed script to populate the database with sample quizzes.

## Steps

1. `uv run alembic upgrade head` — ensure migrations are applied.
2. `uv run python scripts/seed.py` — inserts sample data; duplicates are skipped.

## Output

At least 2 quizzes with 5+ questions each, covering AI development topics.
