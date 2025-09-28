#!/usr/bin/env python3
"""Interactive CLI for second-pass (learn mode) dogfooding."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"
VENV_DIR = PROJECT_ROOT / ".venv"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

# Disable Agents SDK tracing by default; zero-retention orgs cannot upload traces.
os.environ.setdefault("OPENAI_AGENTS_DISABLE_TRACING", "true")

# If the user forgets to activate the venv, try to add its site-packages to sys.path.
if VENV_DIR.exists():
    site_packages_root = VENV_DIR / "lib"
    if site_packages_root.exists():
        for py_dir in site_packages_root.iterdir():
            candidate = py_dir / "site-packages"
            if candidate.exists() and str(candidate) not in sys.path:
                sys.path.insert(0, str(candidate))

try:
    import eval_type_backport  # noqa: F401  # ensure Python 3.9 compatibility
except ImportError as exc:  # pragma: no cover - runtime environment guard
    raise SystemExit(
        "Missing dependency 'eval_type_backport'. Did you run `pip install -r requirements.txt`?"
    ) from exc

try:
    import pydantic_core  # noqa: F401  # verify wheel installed correctly
except ImportError as exc:  # pragma: no cover - runtime environment guard
    raise SystemExit(
        "pydantic-core is missing. Run `python -m pip install --upgrade pip` and then "
        "`pip install --force-reinstall --no-cache-dir -r requirements.txt`."
    ) from exc

from agents import Agent, Runner  # type: ignore

from session_intel.config import DEFAULT_MODEL
from session_intel.knowledge_exchange import KnowledgeExchange
from session_intel.learn_mode import (
    SessionRecap,
    diff_prompts,
    generate_augmented_prompt,
    load_session_recap,
)
from session_intel.session_manager import SessionContext, create_session
from session_intel.summarizer import generate_summary


WELCOME = """\nSession Intelligence – Second Pass (Learn Mode)\nType ':exit' to finish the session.\n"""

EXIT_COMMANDS = {":exit", ":quit", ":end", "exit", "quit", "end"}


def build_agent(recap: Optional[SessionRecap]) -> Agent:
    instructions = [
        "You are a collaborative coding assistant helping developers reinforce prior lessons.",
        "Provide concise, actionable help while tying answers back to previous discoveries when relevant.",
    ]
    if recap and recap.summary_markdown:
        instructions.append("Prior session summary:\n" + recap.summary_markdown)
    if recap and recap.turn_log_tail:
        instructions.append(
            "Recent turn log bullets:\n" + "\n".join(recap.turn_log_tail)
        )
    return Agent(
        name="Codex Task Agent",
        instructions="\n\n".join(instructions),
        model=DEFAULT_MODEL,
    )


def display_recap(recap: Optional[SessionRecap]) -> None:
    if recap is None:
        print("No prior session artifacts found – learn mode will use fresh context.\n")
        return

    print("Loaded prior session:", recap.session_id)
    if recap.summary_markdown:
        print("\n--- Previous Summary ---")
        print(recap.summary_markdown)
    if recap.turn_log_tail:
        print("\n--- Recent Turn Log ---")
        for line in recap.turn_log_tail:
            print(line)
    if recap.recent_user_queries:
        print("\n--- Recent User Questions ---")
        for item in recap.recent_user_queries:
            print(f"- {item}")
    print()


def choose_final_prompt(
    original: str,
    suggestion: str,
    diff: str,
    justification: list[str],
) -> Tuple[Optional[str], bool, bool]:
    print("\n--- Augmentation Preview ---")
    print("Original:")
    print(original)
    print("\nAugmented:")
    print(suggestion)
    if diff:
        print("\nDiff:")
        print(diff)
    print("\nJustification:")
    for item in justification:
        print(f"- {item}")

    while True:
        choice_raw = input("Use augmented prompt? [Y/n/e]: ").strip()
        choice = choice_raw.lower()
        if choice in {"", "y", "yes"}:
            return suggestion, True, False
        if choice in {"n", "no"}:
            return original, False, False
        if choice in EXIT_COMMANDS:
            return None, False, True
        if choice in {"e", "edit"}:
            edited = input("Enter revised prompt: ").strip()
            if edited:
                edited_diff = diff_prompts(original, edited)
                if edited_diff:
                    print("\nDiff vs original:")
                    print(edited_diff)
                return edited, False, False
            print("Edited prompt was empty; keeping original preview.")
        else:
            print("Please enter 'y', 'n', 'e', or an exit command like ':exit'.")


def interactive_loop(session_ctx: SessionContext, recap: Optional[SessionRecap]) -> None:
    agent = build_agent(recap)
    ke = KnowledgeExchange(session_ctx.session_id, session_ctx.documents_dir)

    print(WELCOME)
    print(f"Session ID: {session_ctx.session_id}\n")
    display_recap(recap)

    while True:
        try:
            user_input = input("You> ")
        except (EOFError, KeyboardInterrupt):
            print("\nExiting...")
            break

        if not user_input.strip():
            continue

        stripped_input = user_input.strip()
        command = stripped_input.lower()
        if command in EXIT_COMMANDS:
            break

        augmentation = generate_augmented_prompt(user_input, recap)
        suggestion = augmentation.rewritten_prompt
        diff_text = diff_prompts(user_input, suggestion)
        final_prompt, accepted, exit_requested = choose_final_prompt(
            original=user_input,
            suggestion=suggestion,
            diff=diff_text,
            justification=augmentation.justification,
        )

        if exit_requested:
            print("Ending session...")
            break

        if final_prompt is None:
            print("Skipping turn due to empty prompt.")
            continue

        turn_number = ke.turn_counter + 1
        final_diff = diff_prompts(user_input, final_prompt)
        ke.log_augmented_turn(
            turn=turn_number,
            original=user_input,
            suggestion=suggestion,
            final_prompt=final_prompt,
            suggestion_diff=diff_text,
            final_diff=final_diff,
            justification=augmentation.justification,
            accepted=accepted,
        )
        ke.log_user_message(final_prompt)

        try:
            result = Runner.run_sync(
                agent,
                final_prompt,
                session=session_ctx.session,
            )
            assistant_reply = result.final_output or "(no response)"
        except Exception as exc:  # pragma: no cover - depends on API
            assistant_reply = f"[Error calling agent: {exc}]"

        print(f"Agent> {assistant_reply}\n")
        ke.log_agent_message(assistant_reply)

    summary = generate_summary(ke.turns)
    if summary:
        ke.append_summary(summary)
        print("Session summary appended to learnings.md")
    else:
        print("Skipped summary (missing OpenAI configuration?).")

    print(f"Artifacts stored in: {session_ctx.documents_dir}")


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the second-pass prototype interactively.")
    parser.add_argument(
        "--session-id",
        help="Resume an existing session instead of creating a new one.",
    )
    parser.add_argument(
        "--source-session",
        help="Prior session ID to load for recap/augmentation (defaults to latest).",
    )
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    args = parse_args(argv)
    session_ctx = create_session(args.session_id)
    recap = load_session_recap(args.source_session, exclude_session_id=session_ctx.session_id)
    interactive_loop(session_ctx, recap)
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
