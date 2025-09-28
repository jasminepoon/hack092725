"""Session summarisation helpers using GPT-5."""

from __future__ import annotations

import json
from typing import Iterable, Mapping, Optional

from openai import OpenAI  # type: ignore

from .config import DEFAULT_MODEL


def generate_summary(turns: Iterable[Mapping]) -> Optional[str]:
    """Return a markdown summary of the provided turns using GPT-5."""

    try:
        client = OpenAI()
    except Exception:
        return None

    turns_list = list(turns)
    if not turns_list:
        return None

    convo_json = json.dumps(turns_list, ensure_ascii=False, indent=2)

    system_prompt = (
        "You are an assistant that produces concise session retrospectives for developers. "
        "Summaries must help a human revisit the session quickly."
    )
    user_prompt = (
        "Here is the chronological log of user and agent turns for a coding session.\n"
        "Return markdown with three sections: 'Timeline Highlights' (3-5 bullets), "
        "'Unresolved Questions' (bullets, or 'None'), and 'Suggested Next Reps' (bullets).\n"
        "Focus on knowledge gaps and learning opportunities.\n"
        f"Transcript JSON:```json\n{convo_json}\n```"
    )

    try:
        response = client.responses.create(
            model=DEFAULT_MODEL,
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
    except Exception:
        return None

    try:
        text = response.output_text
    except AttributeError:
        # Fallback for older SDKs
        candidates = [
            block.get("text")
            for block in getattr(response, "output", [])
            if isinstance(block, dict) and block.get("type") == "output_text"
        ]
        text = "\n\n".join(filter(None, candidates))

    return text.strip() if text else None

