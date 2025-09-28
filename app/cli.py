"""CLI entrypoint for the Hack092725 prototype."""
from __future__ import annotations

import argparse
import asyncio
import sys
from typing import Optional

from .config import load_settings
from .knowledge_store import KnowledgeStore
from .orchestrator import PrototypeOrchestrator
from .session import SessionManager


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Hack092725 Agents prototype CLI")
    parser.add_argument("question", nargs="?", help="Question or task for the Task Agent")
    parser.add_argument(
        "--session",
        default="default-session",
        help="Session identifier used for memory persistence",
    )
    parser.add_argument(
        "--learn-mode",
        action="store_true",
        help="Toggle learn mode (second-pass workflow with prior context)",
    )
    parser.add_argument(
        "--skip-synthesis",
        action="store_true",
        help="Skip Knowledge Exchange synthesis/logging (useful for dry runs)",
    )
    return parser


async def _async_main(question: Optional[str], session_id: str, learn_mode: bool, skip_synthesis: bool) -> int:
    settings = load_settings()
    if not settings.has_api_key:
        print("[warning] OPENAI_API_KEY is not set. The agents will fail to call models.", file=sys.stderr)

    store = KnowledgeStore(settings.data_root)
    session_manager = SessionManager(settings.session_db)
    orchestrator = PrototypeOrchestrator(settings, session_manager, store)

    if not question:
        try:
            question = input("Enter your question/task: ").strip()
        except EOFError:
            print("No question provided.", file=sys.stderr)
            return 1

    plan_preview = None
    if learn_mode:
        plan_preview = await orchestrator.build_learn_mode_plan(session_id, question)
        print("\n--- Prior solution recap ---")
        print(plan_preview.plan_result.final_output)
        decision = input("Proceed with execution? (y to run / n to cancel / or add new instructions): ").strip()
        lowered = decision.lower()
        if lowered in {"n", "no", "cancel"}:
            print("Aborting run at user request.")
            await session_manager.close_all()
            return 0
        if lowered not in {"y", "yes", ""}:
            question = f"{question}\n\nAdditional guidance from user: {decision}"

    try:
        run = await orchestrator.run_turn(
            session_id=session_id,
            question=question,
            learn_mode=learn_mode,
            synthesise_learning=not skip_synthesis,
        )
    finally:
        await session_manager.close_all()

    print("\n=== Task Agent Output ===")
    print(run.task_result.final_output)

    if run.task_result.output_guardrail_results:
        print("\n[guardrail] Output guardrail feedback:")
        for result in run.task_result.output_guardrail_results:
            info = getattr(getattr(result, 'output', None), 'output_info', None)
            if info:
                print(f"- {info}")

    if run.knowledge_exchange_result is not None:
        print("\n=== Knowledge Exchange Summary ===")
        print(run.knowledge_exchange_result.final_output)

    usage = run.task_result.context_wrapper.usage if run.task_result.context_wrapper else None
    if usage:
        print("\n[usage stats]")
        print(f"Requests: {usage.requests}")
        print(f"Input tokens: {usage.input_tokens}, Output tokens: {usage.output_tokens}")

    print("\nDocuments stored in:", settings.data_root)

    return 0


def main(argv: Optional[list[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    return asyncio.run(
        _async_main(
            question=args.question,
            session_id=args.session,
            learn_mode=args.learn_mode,
            skip_synthesis=args.skip_synthesis,
        )
    )


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
