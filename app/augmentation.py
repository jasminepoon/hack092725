"""Prompt augmentation helpers for learn mode."""
from __future__ import annotations

import asyncio
import datetime as dt
import difflib
import functools
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional

from openai import OpenAI  # type: ignore

from .knowledge_store import KnowledgeStore


@dataclass(slots=True)
class SessionRecap:
    """Minimal snapshot of prior activity for learn mode."""

    session_id: str
    documents_dir: Path
    summary_markdown: Optional[str]
    turn_log_tail: List[str]
    recent_user_queries: List[str]


@dataclass(slots=True)
class AugmentationResult:
    """Outcome of attempting to rewrite a user prompt."""

    rewritten_prompt: str
    justification: List[str]
    raw_text: str


def diff_prompts(original: str, rewritten: str) -> str:
    """Return a unified diff between the original and rewritten prompts."""

    diff = difflib.unified_diff(
        original.splitlines(),
        rewritten.splitlines(),
        fromfile="original",
        tofile="augmented",
        lineterm="",
    )
    diff_lines = list(diff)
    if len(diff_lines) <= 2:
        return ""
    return "\n".join(diff_lines[2:])


def _normalise_json_text(text: str) -> Optional[dict]:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = "\n".join(
            line for line in stripped.splitlines() if not line.startswith("```")
        ).strip()
    match = re.search(r"\{.*\}", stripped, flags=re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return None


def _render_summary_block(entries: List[str]) -> Optional[str]:
    combined = "\n\n".join(item.strip() for item in entries if item.strip())
    return combined or None


def load_session_recap(store: KnowledgeStore, session_id: str) -> Optional[SessionRecap]:
    """Assemble a recap from the flat-file knowledge store."""

    summary_entries = store.entries(session_id, kind="synthesised_learnings", limit=3)
    turn_entries = store.entries(session_id, limit=8)
    user_entries = store.entries(session_id, kind="user_actions", limit=5)

    if not summary_entries and not turn_entries and not user_entries:
        return None

    summary_markdown = _render_summary_block([entry.content for entry in reversed(summary_entries)])

    turn_log_tail = []
    for entry in reversed(turn_entries):
        snippet = entry.content.strip().splitlines()
        headline = snippet[0] if snippet else "(no content)"
        turn_log_tail.append(f"- [{entry.kind}] {headline}")

    recent_user_queries = [
        entry.content.strip() for entry in reversed(user_entries) if entry.content.strip()
    ]

    documents_dir = store._session_dir(session_id)  # noqa: SLF001 - internal helper reused for compatibility

    return SessionRecap(
        session_id=session_id,
        documents_dir=documents_dir,
        summary_markdown=summary_markdown,
        turn_log_tail=turn_log_tail,
        recent_user_queries=recent_user_queries,
    )


_CLIENT: Optional[OpenAI] = None


def _get_client() -> OpenAI:
    global _CLIENT
    if _CLIENT is None:
        _CLIENT = OpenAI()
    return _CLIENT


def _generate_augmented_prompt_sync(
    original: str,
    recap: Optional[SessionRecap],
    *,
    model: str,
) -> AugmentationResult:
    """Use GPT to rewrite the user message with prior learnings."""

    if not original.strip():
        return AugmentationResult(original, ["No content provided"], raw_text="")

    context_sections: List[str] = []
    if recap:
        if recap.summary_markdown:
            context_sections.append(f"Summary of previous session:\n{recap.summary_markdown}")
        if recap.turn_log_tail:
            context_sections.append(
                "Recent turn log entries:\n" + "\n".join(recap.turn_log_tail)
            )
        if recap.recent_user_queries:
            queries = "\n".join(f"- {q}" for q in recap.recent_user_queries)
            context_sections.append(f"Recent direct user questions:\n{queries}")

    context_blob = "\n\n".join(context_sections) if context_sections else "(No additional context)"

    prompt_user = (
        "You are the Knowledge Exchange agent. Improve the user's request so the task agent "
        "benefits from lessons learned in prior sessions. Use the context below to add reminders, "
        "clarify intent, or highlight prior solutions."
    )

    user_message = (
        f"Original user request:\n```\n{original}\n```\n\n"
        f"Context for augmentation:\n```\n{context_blob}\n```\n\n"
        "Respond with JSON containing `rewritten_prompt` (string) and `justification` (array of short bullet strings)."
    )

    try:
        client = _get_client()
        response = client.responses.create(
            model=model,
            input=[
                {"role": "system", "content": prompt_user},
                {"role": "user", "content": user_message},
            ],
        )
        raw_text = response.output_text
    except Exception as exc:  # pragma: no cover - rely on runtime behaviour
        return AugmentationResult(original, [f"Augmentation failed: {exc}"], raw_text="")

    parsed = _normalise_json_text(raw_text)
    if not parsed:
        return AugmentationResult(original, ["Model response was not valid JSON"], raw_text=raw_text)

    rewritten = parsed.get("rewritten_prompt")
    if not isinstance(rewritten, str) or not rewritten.strip():
        return AugmentationResult(original, ["Model did not provide a rewritten prompt"], raw_text=raw_text)

    justification_raw = parsed.get("justification", [])
    if isinstance(justification_raw, str):
        justification = [justification_raw]
    elif isinstance(justification_raw, Iterable):
        justification = [str(item) for item in justification_raw if str(item).strip()]
    else:
        justification = []

    if not justification:
        justification = ["Model did not provide justification"]

    return AugmentationResult(rewritten.strip(), justification, raw_text=raw_text)


def generate_augmented_prompt(
    original: str,
    recap: Optional[SessionRecap],
    *,
    model: str,
) -> AugmentationResult:
    """Synchronous convenience wrapper (legacy callers)."""

    return _generate_augmented_prompt_sync(original, recap, model=model)


async def generate_augmented_prompt_async(
    original: str,
    recap: Optional[SessionRecap],
    *,
    model: str,
) -> AugmentationResult:
    """Async wrapper that executes augmentation in a thread pool."""

    loop = asyncio.get_running_loop()
    func = functools.partial(_generate_augmented_prompt_sync, original, recap, model=model)
    return await loop.run_in_executor(None, func)


def _count_entries(store: KnowledgeStore, session_id: str, kind: str) -> int:
    return sum(1 for entry in store.iter_all(session_id) if entry.kind == kind)


def log_augmented_turn(
    store: KnowledgeStore,
    session_id: str,
    *,
    original: str,
    suggestion: str,
    final_prompt: str,
    suggestion_diff: str,
    final_diff: str,
    justification: List[str] | None = None,
    accepted: bool = True,
) -> None:
    """Persist augmented prompt details for human review."""

    turn_index = _count_entries(store, session_id, "augmented_turns") + 1
    timestamp = dt.datetime.utcnow().isoformat()

    lines = [
        f"## Turn {turn_index} — {timestamp}",
        "",
        "**Original**",
        "```",
        (original.strip() or "(empty)"),
        "```",
        "",
        "**Suggested Augmentation**",
        "```",
        (suggestion.strip() or "(empty)"),
        "```",
        "",
        "**Final Prompt Sent**",
        "```",
        (final_prompt.strip() or "(empty)"),
        "```",
        "",
        "**Diff (original vs. suggestion)**",
        "```diff",
        (suggestion_diff.strip() or "(no diff)"),
        "```",
        "",
    ]

    if final_prompt.strip() != suggestion.strip():
        lines.extend(
            [
                "**Diff (original vs. final prompt)**",
                "```diff",
                (final_diff.strip() or "(no diff)"),
                "```",
                "",
            ]
        )

    reasons = [f"- {item}" for item in (justification or [])] or ["- (not provided)"]
    lines.extend(
        [
            "**Why it changed**",
            *reasons,
            "",
            "**Human accepted augmentation?**",
            f"- {'Yes' if accepted else 'No'}",
            "",
        ]
    )

    metadata = {
        "turn": turn_index,
        "accepted": accepted,
        "justification": justification or [],
        "suggestion_diff": suggestion_diff,
        "final_diff": final_diff,
        "raw": {
            "original": original,
            "suggestion": suggestion,
            "final_prompt": final_prompt,
        },
        "summary": (
            f"Augmented turn {turn_index}: "
            f"{(justification or ['no change'])[0]}"
        ),
    }

    store.log(
        session_id=session_id,
        kind="augmented_turns",
        content="\n".join(lines),
        metadata=metadata,
    )


__all__ = [
    "SessionRecap",
    "AugmentationResult",
    "diff_prompts",
    "generate_augmented_prompt",
    "generate_augmented_prompt_async",
    "load_session_recap",
    "log_augmented_turn",
]
