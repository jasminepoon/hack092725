"""Agent factories."""
from __future__ import annotations

from typing import Tuple

from agents import Agent, ModelSettings

from .config import PrototypeSettings
from .guardrails import ensure_actionable_response, enforce_scope_guardrail
from .tools import (
    get_recent_learnings,
    log_agent_output,
    log_synthesised_learning,
    log_user_request,
)


def build_task_agent(settings: PrototypeSettings) -> Agent:
    """Create the user-facing task agent."""

    instructions = (
        "You are the Hack092725 Task Agent."
        " Work with human users on software and learning tasks."
        " Always check recent learnings via the provided tool before responding."
        " Explain your reasoning and finish with a 'Next steps' section tailored to the user."
        " Keep tone collaborative and precise."
    )

    return Agent(
        name="Task Agent",
        instructions=instructions,
        model=settings.default_model,
        tools=[get_recent_learnings],
        model_settings=ModelSettings(),
        input_guardrails=[enforce_scope_guardrail],
        output_guardrails=[ensure_actionable_response],
    )


def build_knowledge_exchange_agent(settings: PrototypeSettings) -> Agent:
    """Create the Knowledge Exchange agent responsible for logging and synthesis."""

    instructions = (
        "You are the Hack092725 Knowledge Exchange agent."
        " Your goals: (1) log the latest user request, (2) log the Task Agent output,"
        " (3) synthesise a concise learning entry capturing what changed."
        " Use the logging tools to persist each item."
        " When synthesising, focus on reusable insights, constraints, and decisions."
        " Confirm completion with a short checklist."
    )

    return Agent(
        name="Knowledge Exchange Agent",
        instructions=instructions,
        model=settings.default_model,
        tools=[log_user_request, log_agent_output, log_synthesised_learning],
        model_settings=ModelSettings(),
    )


def build_agents(settings: PrototypeSettings) -> Tuple[Agent, Agent]:
    return build_task_agent(settings), build_knowledge_exchange_agent(settings)


__all__ = ["build_agents", "build_task_agent", "build_knowledge_exchange_agent"]
