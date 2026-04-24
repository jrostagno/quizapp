#!/bin/bash
# Claude Code PreToolUse hook: runs ruff + pytest before `git commit`.
# Only fires when the Bash tool is invoked with a `git commit` command.
# Exit 0 = allow the commit; exit 2 = deny it and show stderr to the agent.

set -uo pipefail

# Read tool input JSON from stdin.
input="$(cat)"

# Extract the command using python3 (bundled on macOS).
cmd="$(printf '%s' "$input" | python3 -c '
import json, sys
try:
    data = json.load(sys.stdin)
    print(data.get("tool_input", {}).get("command", ""))
except Exception:
    print("")
' 2>/dev/null)"

# Pass through anything that is not a `git commit`.
if ! printf '%s' "$cmd" | grep -qE '(^|[[:space:]])git commit([[:space:]]|$)'; then
    exit 0
fi

cd "${CLAUDE_PROJECT_DIR:-$(pwd)}"

echo "🔎 Pre-commit checks: ruff + pytest" >&2

if ! uv run ruff check . >&2; then
    echo "❌ ruff check failed — commit blocked." >&2
    exit 2
fi

if ! uv run ruff format --check . >&2; then
    echo "❌ ruff format --check failed — commit blocked. Run \`uv run ruff format .\`." >&2
    exit 2
fi

if ! uv run pytest >&2; then
    echo "❌ pytest failed — commit blocked." >&2
    exit 2
fi

echo "✅ Pre-commit checks passed." >&2
exit 0
