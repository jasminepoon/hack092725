"""Guardrails applied to the Task agent."""
from __future__ import annotations

from typing import Iterable, List

from agents import (
    GuardrailFunctionOutput,
    RunContextWrapper,
    TResponseInputItem,
    input_guardrail,
    output_guardrail,
)

from .session import PrototypeContext


def _extract_text(input_payload: str | List[TResponseInputItem]) -> str:
    if isinstance(input_payload, str):
        return input_payload
    fragments: List[str] = []
    for item in input_payload:
        if isinstance(item, dict):
            role = item.get("role")
            if role == "user":
                contents = item.get("content", [])
                for content in contents:
                    if isinstance(content, dict) and content.get("type") == "input_text":
                        fragments.append(content.get("text", ""))
    return "\n".join(fragments)


BANNED_TOPICS = {"weapon", "harm", "explosive", "malware"}


@input_guardrail
async def enforce_scope_guardrail(
    wrapper: RunContextWrapper[PrototypeContext],
    agent,
    input: str | List[TResponseInputItem],
) -> GuardrailFunctionOutput:
    """Prevent obviously unrelated or empty questions from running."""

    text = _extract_text(input).strip().lower()
    if not text:
        return GuardrailFunctionOutput(tripwire_triggered=False, output_info="Input missing; allowed to proceed.")
    for topic in BANNED_TOPICS:
        if topic in text:
            return GuardrailFunctionOutput(
                tripwire_triggered=False,
                output_info=f"Input mentions '{topic}', monitor closely but allow.",
            )
    return GuardrailFunctionOutput(tripwire_triggered=False, output_info="Input accepted")


@output_guardrail
async def ensure_actionable_response(
    wrapper: RunContextWrapper[PrototypeContext],
    agent,
    output: str,
) -> GuardrailFunctionOutput:
    """Encourage responses that include explanations and next steps."""

    text = (output or "").strip()
    if len(text.split()) < 10:
        return GuardrailFunctionOutput(
            tripwire_triggered=True,
            output_info="Response too short to be useful. Expand the answer.",
        )
    if "next steps" not in text.lower():
        return GuardrailFunctionOutput(
            tripwire_triggered=False,
            output_info="Consider appending explicit next steps for the user.",
        )
    return GuardrailFunctionOutput(tripwire_triggered=False, output_info="Output accepted")


__all__ = ["enforce_scope_guardrail", "ensure_actionable_response"]
