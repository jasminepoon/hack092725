"""High-level integration helpers for embedding Session Intelligence in a CLI."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional

from .knowledge_exchange import KnowledgeExchange
from .learn_mode import (
    AugmentationResult,
    SessionRecap,
    diff_prompts,
    generate_augmented_prompt,
    load_session_recap,
)
from .session_manager import SessionContext, create_session
from .summarizer import generate_summary


class SessionMode(str, Enum):
    """Enum representing the supported run modes."""

    FIRST_PASS = "first-pass"
    LEARN = "learn"


EXIT_COMMANDS = {":exit", ":quit", ":end", "exit", "quit", "end"}


@dataclass
class TurnPreview:
    """Details surfaced to the CLI before the user confirms a prompt."""

    original: str
    suggestion: str
    justification: List[str]
    diff_original_suggestion: str
    requires_confirmation: bool


@dataclass
class SessionIntelAdapter:
    """Facade that keeps CLI code unaware of logging/augmentation internals."""

    mode: SessionMode
    session_ctx: SessionContext
    knowledge_exchange: KnowledgeExchange
    recap: Optional[SessionRecap]

    @classmethod
    def start(
        cls,
        mode: SessionMode,
        *,
        session_id: Optional[str] = None,
        source_session: Optional[str] = None,
    ) -> "SessionIntelAdapter":
        session_ctx = create_session(session_id)
        ke = KnowledgeExchange(session_ctx.session_id, session_ctx.documents_dir)

        recap: Optional[SessionRecap] = None
        if mode == SessionMode.LEARN:
            recap = load_session_recap(source_session, exclude_session_id=session_ctx.session_id)

        return cls(mode=mode, session_ctx=session_ctx, knowledge_exchange=ke, recap=recap)

    # ------------------------------------------------------------------
    # Agent setup
    # ------------------------------------------------------------------
    def _instruction_lines(self) -> List[str]:
        instructions = [
            "You are a collaborative coding assistant helping developers learn new skills.",
            "Provide concise, actionable help while calling out knowledge gaps to revisit.",
        ]
        if self.mode == SessionMode.LEARN:
            instructions.append(
                "Lean on previous insights to accelerate progress; remind the developer of "
                "strategies that worked last time."
            )
            if self.recap and self.recap.summary_markdown:
                instructions.append("Previous session summary:\n" + self.recap.summary_markdown)
            if self.recap and self.recap.turn_log_tail:
                instructions.append(
                    "Recent turn log bullets:\n" + "\n".join(self.recap.turn_log_tail)
                )

        return instructions

    def compose_instructions(self) -> str:
        """Return a newline-separated instruction preamble for downstream agents."""

        return "\n\n".join(self._instruction_lines())

    # ------------------------------------------------------------------
    # Turn preparation & logging
    # ------------------------------------------------------------------
    def prepare_turn(self, user_input: str) -> TurnPreview:
        """Return augmentation preview and metadata for the CLI."""

        if self.mode == SessionMode.LEARN:
            augmentation = self._augment(user_input)
            diff_text = diff_prompts(user_input, augmentation.rewritten_prompt)
            return TurnPreview(
                original=user_input,
                suggestion=augmentation.rewritten_prompt,
                justification=augmentation.justification,
                diff_original_suggestion=diff_text,
                requires_confirmation=True,
            )

        # First-pass mode: no rewrite, but keep contract consistent.
        return TurnPreview(
            original=user_input,
            suggestion=user_input,
            justification=["First-pass mode (no augmentation applied)."],
            diff_original_suggestion="",
            requires_confirmation=False,
        )

    def record_user_turn(
        self,
        preview: TurnPreview,
        final_prompt: str,
        *,
        accepted: bool,
    ) -> None:
        """Persist the chosen prompt and augmentation metadata."""

        if self.mode == SessionMode.LEARN:
            suggestion_diff = preview.diff_original_suggestion
            final_diff = diff_prompts(preview.original, final_prompt)
            self.knowledge_exchange.log_augmented_turn(
                turn=self.knowledge_exchange.turn_counter + 1,
                original=preview.original,
                suggestion=preview.suggestion,
                final_prompt=final_prompt,
                suggestion_diff=suggestion_diff,
                final_diff=final_diff,
                justification=preview.justification,
                accepted=accepted,
            )

        self.knowledge_exchange.log_user_message(final_prompt)

    def record_agent_turn(self, content: str) -> None:
        self.knowledge_exchange.log_agent_message(content)

    # ------------------------------------------------------------------
    # Session teardown
    # ------------------------------------------------------------------
    def finalize(self) -> Optional[str]:
        summary = generate_summary(self.knowledge_exchange.turns)
        if summary:
            self.knowledge_exchange.append_summary(summary)
        return summary

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _augment(self, user_input: str) -> AugmentationResult:
        return generate_augmented_prompt(user_input, self.recap)


__all__ = [
    "SessionIntelAdapter",
    "SessionMode",
    "TurnPreview",
    "EXIT_COMMANDS",
]
