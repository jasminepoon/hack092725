"""High-level orchestration of Task and Knowledge Exchange agents."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from agents import RunConfig, RunResult, Runner, trace

from .agents import build_agents
from .config import PrototypeSettings
from .knowledge_store import KnowledgeStore
from .session import PrototypeContext, SessionManager


@dataclass(slots=True)
class PlanPreview:
    plan_result: RunResult
    digest: str


@dataclass(slots=True)
class PrototypeRun:
    task_result: RunResult
    knowledge_exchange_result: Optional[RunResult]
    digest: str


class PrototypeOrchestrator:
    def __init__(self, settings: PrototypeSettings, session_manager: SessionManager, knowledge_store: KnowledgeStore) -> None:
        self.settings = settings
        self.session_manager = session_manager
        self.knowledge_store = knowledge_store
        self.task_agent, self.ke_agent = build_agents(settings)


    async def build_learn_mode_plan(self, session_id: str, question: str) -> PlanPreview:
        session = self.session_manager.get(session_id)
        digest = self.knowledge_store.render_digest(session_id)
        context = PrototypeContext(
            session_id=session_id,
            knowledge_store=self.knowledge_store,
            learn_mode=True,
            previous_learnings=[digest],
        )
        plan_prompt = (
            "You previously solved a similar task. Summarize the prior approach in a clear plan, "
            "then ask the human if they would like to proceed with the same steps. "
            "Do not execute the task yet.\n\n"
            "Previous learnings:\n"
            f"{digest}\n\n"
            "New request:\n"
            f"{question}"
        )
        run_config = RunConfig(workflow_name=self.settings.workflow_name, tracing_disabled=True)
        plan_result = await Runner.run(
            self.task_agent,
            plan_prompt,
            context=context,
            session=session,
            run_config=run_config,
        )
        return PlanPreview(plan_result=plan_result, digest=digest)

    async def run_turn(
        self,
        session_id: str,
        question: str,
        *,
        learn_mode: bool = False,
        synthesise_learning: bool = True,
    ) -> PrototypeRun:
        session = self.session_manager.get(session_id)
        digest = self.knowledge_store.render_digest(session_id)

        context = PrototypeContext(
            session_id=session_id,
            knowledge_store=self.knowledge_store,
            learn_mode=learn_mode,
            previous_learnings=[digest],
        )

        task_prompt_parts = [
            f"Session: {session_id}",
            digest,
            "User request:",
            question,
        ]
        if learn_mode:
            task_prompt_parts.append(
                "Learn mode is ON. Offer the prior approach, ask whether to reuse it, and highlight differences before executing."
            )
        task_prompt = "\n\n".join(task_prompt_parts)

        run_config = RunConfig(workflow_name=self.settings.workflow_name, tracing_disabled=True)

        with trace(
            self.settings.workflow_name,
            metadata={"session_id": session_id, "learn_mode": str(learn_mode)}
        ):
            task_result = await Runner.run(
                self.task_agent,
                task_prompt,
                context=context,
                session=session,
                run_config=run_config,
            )

            ke_result: Optional[RunResult] = None
            if synthesise_learning:
                ke_prompt = (
                    "You are finishing a session."
                    " Use your tools to (1) log the user request, (2) log the task output,"
                    " (3) write a distilled learning with actionable next steps." \
                    f"\n\nUser request:\n{question}\n\nTask agent output:\n{task_result.final_output}"
                )
                ke_context = PrototypeContext(
                    session_id=session_id,
                    knowledge_store=self.knowledge_store,
                    learn_mode=learn_mode,
                )
                ke_result = await Runner.run(
                    self.ke_agent,
                    ke_prompt,
                    context=ke_context,
                    run_config=run_config,
                )

        return PrototypeRun(task_result=task_result, knowledge_exchange_result=ke_result, digest=digest)


__all__ = ["PrototypeOrchestrator", "PrototypeRun", "PlanPreview"]
