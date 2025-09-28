#!/usr/bin/env python3
"""Interactive CLI for first-pass (gap capture mode) dogfooding."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Optional

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
from session_intel.session_manager import SessionContext, create_session
from session_intel.summarizer import generate_summary


WELCOME = """\nSession Intelligence – First Pass\nType ':exit' to finish the session.\n"""


def build_agent() -> Agent:
    return Agent(
        name="Codex Task Agent",
        instructions=(
            "You are a collaborative coding assistant helping developers learn new skills. "
            "Provide actionable, concise help while calling out gaps the user should practice."
        ),
        model=DEFAULT_MODEL,
    )


def interactive_loop(session_ctx: SessionContext) -> None:
    agent = build_agent()
    ke = KnowledgeExchange(session_ctx.session_id, session_ctx.documents_dir)

    print(WELCOME)
    print(f"Session ID: {session_ctx.session_id}\n")

    while True:
        try:
            user_input = input("You> ")
        except (EOFError, KeyboardInterrupt):
            print("\nExiting...")
            break

        if not user_input.strip():
            continue

        if user_input.strip().lower() in {":exit", ":quit"}:
            break

        ke.log_user_message(user_input)

        try:
            result = Runner.run_sync(
                agent,
                user_input,
                session=session_ctx.session,
            )
            assistant_reply = result.final_output or "(no response)"
        except Exception as exc:  # pragma: no cover - depends on API key
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
    parser = argparse.ArgumentParser(description="Run the first-pass prototype interactively.")
    parser.add_argument(
        "--session-id",
        help="Resume an existing session instead of creating a new one.",
    )
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    args = parse_args(argv)
    session_ctx = create_session(args.session_id)
    interactive_loop(session_ctx)
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
