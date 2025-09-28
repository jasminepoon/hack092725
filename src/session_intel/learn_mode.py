"""Helpers for learn-mode (second pass) workflows."""

from __future__ import annotations

import difflib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional

from openai import OpenAI  # type: ignore

from .config import DEFAULT_MODEL, DOCUMENTS_ROOT


@dataclass
class SessionRecap:
    """Minimal snapshot of a prior session for learn mode."""

    session_id: str
    documents_dir: Path
    summary_markdown: Optional[str]
    turn_log_tail: List[str]
    recent_user_queries: List[str]


@dataclass
class AugmentationResult:
    """Outcome of attempting to rewrite a user prompt."""

    rewritten_prompt: str
    justification: List[str]
    raw_text: str


def _list_session_dirs() -> List[Path]:
    if not DOCUMENTS_ROOT.exists():
        return []
    return sorted(
        [
            path
            for path in DOCUMENTS_ROOT.iterdir()
            if path.is_dir()
        ],
        key=lambda p: p.name,
    )


def pick_source_session(
    session_id: Optional[str] = None,
    *,
    exclude_session_id: Optional[str] = None,
) -> Optional[Path]:
    """Return the documents folder for the requested (or latest) session."""

    if session_id is not None:
        candidate = DOCUMENTS_ROOT / session_id
        return candidate if candidate.exists() else None

    sessions = _list_session_dirs()
    if not sessions:
        return None
    for path in reversed(sessions):
        if path.name != exclude_session_id:
            return path
    return None


def _read_learnings(path: Path) -> tuple[Optional[str], List[str]]:
    if not path.exists():
        return None, []
    content = path.read_text(encoding="utf-8")
    summary_section = None
    if "## Session Summary" in content:
        summary_section = content.split("## Session Summary", 1)[1].strip()
    lines = [line.strip() for line in content.splitlines() if line.startswith("- Turn ")]
    return summary_section, lines[-8:]


def _read_recent_user_queries(path: Path, limit: int = 5) -> List[str]:
    if not path.exists():
        return []
    queries: List[str] = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            content = payload.get("content")
            if isinstance(content, str):
                queries.append(content.strip())
    return queries[-limit:]


def load_session_recap(
    session_id: Optional[str] = None,
    *,
    exclude_session_id: Optional[str] = None,
) -> Optional[SessionRecap]:
    """Load summary and recent interactions from a prior session."""

    session_dir = pick_source_session(session_id, exclude_session_id=exclude_session_id)
    if session_dir is None:
        return None

    summary, turn_tail = _read_learnings(session_dir / "learnings.md")
    recent_queries = _read_recent_user_queries(session_dir / "user_actions.jsonl")

    return SessionRecap(
        session_id=session_dir.name,
        documents_dir=session_dir,
        summary_markdown=summary,
        turn_log_tail=turn_tail,
        recent_user_queries=recent_queries,
    )


def diff_prompts(original: str, rewritten: str) -> str:
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
    # Drop header lines for a compact view.
    return "\n".join(diff_lines[2:])


def _normalise_json_text(text: str) -> Optional[dict]:
    stripped = text.strip()
    if stripped.startswith("```"):
        # Remove surrounding code fences if present.
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


def generate_augmented_prompt(
    original: str,
    recap: Optional[SessionRecap],
    model: str = DEFAULT_MODEL,
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
                "Recent turn log bullets:\n" + "\n".join(recap.turn_log_tail)
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
        client = OpenAI()
        response = client.responses.create(
            model=model,
            input=[
                {"role": "system", "content": prompt_user},
                {"role": "user", "content": user_message},
            ],
        )
        raw_text = response.output_text
    except Exception as exc:
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
