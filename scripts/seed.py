"""Idempotent seed script for QuizApp.

Run via `uv run python -m scripts.seed`. Safe to re-run — quizzes are skipped
when a row with the same title already exists.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.attempts import models as _attempts_models  # noqa: F401 — register mappers
from app.core.config import get_settings
from app.notifications import models as _notifications_models  # noqa: F401
from app.quizzes.models import Option, Question, Quiz
from app.users import models as _users_models  # noqa: F401

logger = logging.getLogger(__name__)


QUIZZES: list[dict[str, Any]] = [
    {
        "title": "Agent Fundamentals",
        "description": (
            "Core concepts behind AI agents: goals, autonomy, tool use, and the ReAct loop."
        ),
        "questions": [
            {
                "body": "What best describes an **AI agent**?",
                "explanation": (
                    "An agent is a system that *perceives* its environment, *decides*, "
                    "and *acts* to achieve a goal — often iteratively."
                ),
                "options": [
                    {
                        "body": "A system that perceives, decides, and acts toward a goal",
                        "is_correct": True,
                    },
                    {"body": "A deterministic script with no feedback loop", "is_correct": False},
                    {"body": "A static database of prompts", "is_correct": False},
                ],
            },
            {
                "body": "What is the **ReAct pattern**?",
                "explanation": (
                    "ReAct interleaves **Reasoning** (chain-of-thought) with **Acting** "
                    "(tool use), letting the model plan, act, observe, and iterate."
                ),
                "options": [
                    {"body": "A UI framework for React.js", "is_correct": False},
                    {
                        "body": "Interleaving reasoning steps with tool-use actions",
                        "is_correct": True,
                    },
                    {"body": "A reinforcement-learning algorithm", "is_correct": False},
                ],
            },
            {
                "body": "Why do agents need **tools**?",
                "explanation": (
                    "LLMs are stateless reasoners. Tools let them read fresh data, "
                    "mutate systems, and offload exact computation."
                ),
                "options": [
                    {
                        "body": (
                            "To extend the model beyond its training knowledge and take actions"
                        ),
                        "is_correct": True,
                    },
                    {"body": "To increase the token window", "is_correct": False},
                    {"body": "To improve sampling temperature", "is_correct": False},
                ],
            },
            {
                "body": "Which statement about **agent autonomy** is most accurate?",
                "explanation": (
                    "Autonomy is a spectrum — from suggestion-only copilots to fully "
                    "autonomous agents. Production systems usually bound it with "
                    "approvals, scopes, and budgets."
                ),
                "options": [
                    {"body": "Agents must always be fully autonomous", "is_correct": False},
                    {
                        "body": "Autonomy is a spectrum, constrained by guardrails in production",
                        "is_correct": True,
                    },
                    {"body": "Autonomy is unrelated to safety", "is_correct": False},
                ],
            },
            {
                "body": "What role does **memory** play in agents?",
                "explanation": (
                    "Memory holds prior state, user facts, and prior tool outputs, so "
                    "the agent can maintain coherence across turns."
                ),
                "options": [
                    {"body": "It has no role — agents are stateless", "is_correct": False},
                    {"body": "It lets agents retain context across turns", "is_correct": True},
                    {"body": "It only caches API keys", "is_correct": False},
                ],
            },
        ],
    },
    {
        "title": "Prompt Engineering Basics",
        "description": (
            "Fundamentals of prompting LLMs: system prompts, examples, reasoning, "
            "and token economics."
        ),
        "questions": [
            {
                "body": "What is a **prompt**?",
                "explanation": (
                    "A prompt is the input given to a model — system messages, user "
                    "messages, examples, and tool definitions."
                ),
                "options": [
                    {"body": "The training dataset", "is_correct": False},
                    {"body": "The input text that steers a model's output", "is_correct": True},
                    {"body": "The model's output", "is_correct": False},
                ],
            },
            {
                "body": "What is **few-shot prompting**?",
                "explanation": (
                    "Few-shot prompting includes a handful of input/output examples in "
                    "the prompt to show the model the desired format and behavior."
                ),
                "options": [
                    {
                        "body": "Providing example input/output pairs in the prompt",
                        "is_correct": True,
                    },
                    {"body": "Fine-tuning the model on new data", "is_correct": False},
                    {"body": "Lowering the temperature parameter", "is_correct": False},
                ],
            },
            {
                "body": "What is **chain-of-thought** prompting?",
                "explanation": (
                    "Chain-of-thought encourages the model to reason **step by step** "
                    "before answering — often by adding 'think step by step' or by "
                    "showing worked-out examples."
                ),
                "options": [
                    {"body": "Asking the model to reason step by step", "is_correct": True},
                    {"body": "Chaining multiple unrelated prompts", "is_correct": False},
                    {"body": "A database indexing technique", "is_correct": False},
                ],
            },
            {
                "body": "What is the purpose of a **system prompt**?",
                "explanation": (
                    "The system prompt sets the model's *role, style, and constraints* "
                    "for the whole conversation — a global instruction layer above "
                    "individual user turns."
                ),
                "options": [
                    {"body": "To inject secrets into the request", "is_correct": False},
                    {
                        "body": "To define role, style, and constraints for the session",
                        "is_correct": True,
                    },
                    {"body": "To replace the user's turn", "is_correct": False},
                ],
            },
            {
                "body": "Which factor most directly affects **prompt cost** per request?",
                "explanation": (
                    "Token count (input + output) drives cost directly. Temperature and "
                    "streaming affect behavior/latency, not billing."
                ),
                "options": [
                    {"body": "Model temperature", "is_correct": False},
                    {"body": "The total number of input + output tokens", "is_correct": True},
                    {"body": "Whether the response is streamed", "is_correct": False},
                ],
            },
        ],
    },
]


async def seed_quizzes(session: AsyncSession) -> list[Quiz]:
    """Insert missing quizzes. Returns the list of quizzes created in this call."""

    created: list[Quiz] = []
    for quiz_data in QUIZZES:
        existing = (
            await session.execute(select(Quiz).where(Quiz.title == quiz_data["title"]))
        ).scalar_one_or_none()
        if existing is not None:
            logger.info("skipping %s — already seeded", quiz_data["title"])
            continue

        quiz = Quiz(title=quiz_data["title"], description=quiz_data["description"])
        for q_idx, q_data in enumerate(quiz_data["questions"], start=1):
            question = Question(
                body=q_data["body"],
                explanation=q_data["explanation"],
                position=q_idx,
            )
            for o_idx, o_data in enumerate(q_data["options"], start=1):
                question.options.append(
                    Option(
                        body=o_data["body"],
                        is_correct=o_data["is_correct"],
                        position=o_idx,
                    )
                )
            quiz.questions.append(question)

        session.add(quiz)
        created.append(quiz)
        logger.info("seeded %s", quiz_data["title"])

    await session.commit()
    return created


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    try:
        async with session_factory() as session:
            created = await seed_quizzes(session)
        print(f"Seeded {len(created)} new quizzes (existing quizzes were skipped).")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
