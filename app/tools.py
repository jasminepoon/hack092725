"""Function tools shared by Task and Knowledge Exchange agents."""
from __future__ import annotations

from typing import Any, List, Optional

from agents import RunContextWrapper, function_tool

from .knowledge_store import KnowledgeEntry
from .session import PrototypeContext


def _require_context(wrapper: RunContextWrapper[PrototypeContext]) -> PrototypeContext:
    context = wrapper.context
    if context is None:
        raise ValueError("PrototypeContext is required for this tool")
    return context


@function_tool
def log_user_request(
    wrapper: RunContextWrapper[PrototypeContext],
    question: str,
    tags: Optional[List[str]] = None,
) -> str:
    """Persist the latest user question in the knowledge store."""

    context = _require_context(wrapper)
    entry = context.knowledge_store.log(
        session_id=context.session_id,
        kind="user_actions",
        content=question.strip(),
        metadata={"tags": tags or []},
    )
    return f"Logged user request as {entry.path.name}"


@function_tool
def log_agent_output(
    wrapper: RunContextWrapper[PrototypeContext],
    output: str,
    summary: Optional[str] = None,
) -> str:
    """Persist the task agent's output."""

    context = _require_context(wrapper)
    entry = context.knowledge_store.log(
        session_id=context.session_id,
        kind="agent_actions",
        content=output.strip(),
        metadata={"summary": summary or output.strip().splitlines()[0][:120]},
    )
    return f"Logged agent output as {entry.path.name}"


@function_tool
def log_synthesised_learning(
    wrapper: RunContextWrapper[PrototypeContext],
    learning: str,
    summary: Optional[str] = None,
) -> str:
    """Store distilled learnings for future sessions."""

    context = _require_context(wrapper)
    entry = context.knowledge_store.log(
        session_id=context.session_id,
        kind="synthesised_learnings",
        content=learning.strip(),
        metadata={"summary": summary or learning.strip().splitlines()[0][:120]},
    )
    return f"Logged synthesised learning as {entry.path.name}"


@function_tool
def get_recent_learnings(
    wrapper: RunContextWrapper[PrototypeContext],
    limit: int = 3,
) -> str:
    """Return a digest of recent entries for the session."""

    context = _require_context(wrapper)
    entries: list[KnowledgeEntry] = context.knowledge_store.entries(context.session_id, limit=limit)
    if not entries:
        return "No previous learnings recorded."

    lines = [f"Session digest for {context.session_id}:"]
    for entry in entries:
        summary = entry.metadata.get("summary") or entry.content.splitlines()[0][:160]
        lines.append(f"- ({entry.kind}) {summary}")
    return "\n".join(lines)


__all__ = [
    "log_user_request",
    "log_agent_output",
    "log_synthesised_learning",
    "get_recent_learnings",
]
