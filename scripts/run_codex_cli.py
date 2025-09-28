#!/usr/bin/env python3
"""Unified Codex CLI proof-of-concept with embedded session intelligence."""

from __future__ import annotations

import argparse
import os
import sys
import threading
import time
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

from session_intel.adapter import (
    EXIT_COMMANDS,
    SessionIntelAdapter,
    SessionMode,
    TurnPreview,
)
from session_intel.codex_backend import CodexCliSession, CodexError


WELCOME = """\nCodex CLI (Session Intelligence Prototype)\nType ':exit' to finish the session.\n"""


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Codex CLI with embedded session intelligence.")
    parser.add_argument(
        "--mode",
        choices=[SessionMode.FIRST_PASS.value, SessionMode.LEARN.value],
        default=SessionMode.FIRST_PASS.value,
        help="Choose between first-pass logging or learn mode augmentation.",
    )
    parser.add_argument("--session-id", help="Optional session identifier to resume.")
    parser.add_argument(
        "--source-session",
        help="When in learn mode, which prior session to load for recap (defaults to latest).",
    )
    return parser.parse_args(argv)


def display_recap(adapter: SessionIntelAdapter) -> None:
    if adapter.mode != SessionMode.LEARN:
        return
    recap = adapter.recap
    if recap is None:
        print("No prior session artifacts found – learn mode will use fresh context.\n")
        return

    print(f"Loaded prior session: {recap.session_id}")
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


def confirm_prompt(preview: TurnPreview) -> Tuple[Optional[str], bool, bool]:
    print("\n--- Augmentation Preview ---")
    print("Original:")
    print(preview.original)
    print("\nAugmented:")
    print(preview.suggestion)
    if preview.diff_original_suggestion:
        print("\nDiff:")
        print(preview.diff_original_suggestion)
    print("\nJustification:")
    for item in preview.justification:
        print(f"- {item}")

    while True:
        choice_raw = input("Use augmented prompt? [Y/n/e]: ").strip()
        choice = choice_raw.lower()
        if choice in {"", "y", "yes"}:
            return preview.suggestion, True, False
        if choice in {"n", "no"}:
            return preview.original, False, False
        if choice in EXIT_COMMANDS:
            return None, False, True
        if choice in {"e", "edit"}:
            edited = input("Enter revised prompt: ").strip()
            if edited:
                return edited, False, False
            print("Edited prompt was empty; keeping original preview.")
        else:
            print("Please enter 'y', 'n', 'e', or an exit command like ':exit'.")


def interactive_loop(adapter: SessionIntelAdapter) -> None:
    codex_session = CodexCliSession(workdir=PROJECT_ROOT)
    instructions_preface = adapter.compose_instructions().strip()
    preface_sent = False

    def start_wait_notifier() -> tuple[threading.Event, threading.Thread]:
        stop_event = threading.Event()

        def notifier() -> None:
            start = time.monotonic()
            milestone = 15
            while not stop_event.wait(5):
                elapsed = time.monotonic() - start
                if elapsed >= milestone:
                    print(
                        f"... still waiting on Codex ({int(elapsed)}s elapsed)",
                        flush=True,
                    )
                    milestone += 15

        thread = threading.Thread(target=notifier, daemon=True)
        thread.start()
        return stop_event, thread

    print(WELCOME)
    print(f"Mode: {adapter.mode.value}")
    print(f"Session ID: {adapter.session_ctx.session_id}\n")
    display_recap(adapter)

    while True:
        try:
            user_input = input("You> ")
        except (EOFError, KeyboardInterrupt):
            print("\nExiting...")
            break

        if not user_input.strip():
            continue

        stripped = user_input.strip()
        if stripped.lower() in EXIT_COMMANDS:
            break

        preview = adapter.prepare_turn(user_input)
        final_prompt = preview.suggestion
        accepted = True
        exit_requested = False

        if preview.requires_confirmation:
            final_prompt, accepted, exit_requested = confirm_prompt(preview)

        if exit_requested:
            print("Ending session...")
            break

        if final_prompt is None or not final_prompt.strip():
            print("Skipping turn due to empty prompt.")
            continue

        prompt_to_send = final_prompt

        if not preface_sent and instructions_preface:
            prompt_to_send = f"{instructions_preface}\n\n{prompt_to_send}".strip()
            preface_sent = True

        adapter.record_user_turn(
            preview,
            prompt_to_send,
            accepted=accepted and final_prompt == preview.suggestion,
        )

        wait_event, wait_thread = start_wait_notifier()
        start_time = time.monotonic()
        try:
            assistant_reply, reasoning = codex_session.send(prompt_to_send)
        except CodexError as exc:  # pragma: no cover - depends on Codex CLI env
            assistant_reply = f"[Codex error: {exc}]"
            reasoning = []
            if exc.stdout:
                print("[Codex stdout]\n" + exc.stdout.strip())
            if exc.stderr:
                print("[Codex stderr]\n" + exc.stderr.strip())
        finally:
            wait_event.set()
            wait_thread.join(timeout=0.2)

        elapsed = time.monotonic() - start_time
        if elapsed >= 15:
            print(f"(Codex responded in {elapsed:.1f}s)")

        if reasoning:
            for line in reasoning:
                print(f"(thinking) {line}")

        print(f"Codex> {assistant_reply}\n")
        adapter.record_agent_turn(
            assistant_reply if not reasoning else "\n".join([*reasoning, assistant_reply])
        )

    summary = adapter.finalize()
    if summary:
        print("Session summary appended to learnings.md")
    else:
        print("Skipped summary (missing OpenAI configuration?).")

    if codex_session.session_id:
        session_id_path = adapter.session_ctx.documents_dir / "codex_session_id.txt"
        session_id_path.write_text(codex_session.session_id + "\n", encoding="utf-8")

    print(f"Artifacts stored in: {adapter.session_ctx.documents_dir}")


def main(argv: Optional[list[str]] = None) -> int:
    args = parse_args(argv)
    mode = SessionMode(args.mode)
    adapter = SessionIntelAdapter.start(
        mode,
        session_id=args.session_id,
        source_session=args.source_session,
    )
    interactive_loop(adapter)
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
