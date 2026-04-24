---
name: run-checks
description: Run all QuizApp quality checks — ruff lint, ruff format check, and pytest. Trigger before any commit or on "run checks", "are tests green?", "verify quality".
---

# run-checks

Run the full quality gate. All three must pass.

## Command

```bash
uv run ruff check . && uv run ruff format --check . && uv run pytest
```

Any failure blocks the commit (same as the git pre-commit hook).
