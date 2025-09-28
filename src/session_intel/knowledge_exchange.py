"""Knowledge Exchange agent helpers for logging and augmentation."""

from __future__ import annotations

import datetime as dt
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List

from .config import LEARNINGS_HEADER_TEMPLATE, SUMMARY_HEADER


def _append_jsonl(path: Path, record: Dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")


def _ensure_markdown(path: Path, session_id: str, ts: dt.datetime) -> None:
    if path.exists():
        return
    header = LEARNINGS_HEADER_TEMPLATE.format(session_id=session_id, timestamp=ts.isoformat())
    path.write_text(header, encoding="utf-8")


@dataclass
class KnowledgeExchange:
    """Handles logging of user/agent actions and markdown updates."""

    session_id: str
    documents_dir: Path
    turn_counter: int = 0
    turns: List[Dict] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.user_actions_path = self.documents_dir / "user_actions.jsonl"
        self.agent_actions_path = self.documents_dir / "agent_actions.jsonl"
        self.learnings_path = self.documents_dir / "learnings.md"
        self.augmented_path = self.documents_dir / "augmented_turns.md"
        _ensure_markdown(self.learnings_path, self.session_id, dt.datetime.utcnow())

    # Logging helpers -----------------------------------------------------
    def log_user_message(self, content: str) -> None:
        self.turn_counter += 1
        record = {
            "timestamp": dt.datetime.utcnow().isoformat(),
            "turn": self.turn_counter,
            "role": "user",
            "content": content,
        }
        _append_jsonl(self.user_actions_path, record)
        self.turns.append(record)
        self._append_markdown_entry(record)

    def log_agent_message(self, content: str) -> None:
        record = {
            "timestamp": dt.datetime.utcnow().isoformat(),
            "turn": self.turn_counter,
            "role": "agent",
            "content": content,
        }
        _append_jsonl(self.agent_actions_path, record)
        self.turns.append(record)
        self._append_markdown_entry(record)

    def _append_markdown_entry(self, record: Dict) -> None:
        if "role" not in record:
            return
        role = record["role"].capitalize()
        content = record.get("content", "").strip()
        if not content:
            content = "(no content)"
        line = f"- Turn {record.get('turn', '?')} – **{role}**: {content}\n"
        with self.learnings_path.open("a", encoding="utf-8") as fh:
            fh.write(line)

    # Summary -------------------------------------------------------------
    def append_summary(self, summary_markdown: str) -> None:
        with self.learnings_path.open("a", encoding="utf-8") as fh:
            fh.write(SUMMARY_HEADER)
            fh.write(summary_markdown.strip() + "\n")

    # Augmentation -------------------------------------------------------
    def log_augmented_turn(
        self,
        turn: int,
        original: str,
        suggestion: str,
        final_prompt: str,
        suggestion_diff: str,
        final_diff: str,
        justification: List[str] | None = None,
        accepted: bool = True,
    ) -> None:
        """Persist augmented prompt details for human review."""

        if not self.augmented_path.exists():
            header = (
                "# Augmented Turns\n\n"
                "Entries capture how the Knowledge Exchange agent rewrote prompts before "
                "they were sent to the task agent.\n\n"
            )
            self.augmented_path.write_text(header, encoding="utf-8")

        timestamp = dt.datetime.utcnow().isoformat()
        lines = [
            f"## Turn {turn} — {timestamp}",
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
        ]

        suggestion_diff = suggestion_diff.strip()
        final_diff = final_diff.strip()

        lines.extend(
            [
                "**Diff (original vs. suggestion)**",
                "```diff",
                suggestion_diff or "(no diff)",
                "```",
                "",
            ]
        )

        if final_prompt.strip() != suggestion.strip():
            lines.extend(
                [
                    "**Diff (original vs. final prompt)**",
                    "```diff",
                    final_diff or "(no diff)",
                    "```",
                    "",
                ]
            )

        reasons = [f"- {item}" for item in (justification or [])] or ["- (not provided)"]
        lines.extend([
            "**Why it changed**",
            *reasons,
            "",
            "**Human accepted augmentation?**",
            f"- {'Yes' if accepted else 'No'}",
            "",
        ])

        with self.augmented_path.open("a", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")
