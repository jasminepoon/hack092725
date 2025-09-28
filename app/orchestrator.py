"""High-level orchestration of Task and Knowledge Exchange agents."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import List, Optional

from agents import RunConfig, RunResult, Runner, trace

from .agents import build_agents
from .augmentation import (
    AugmentationResult,
    SessionRecap,
    diff_prompts,
    generate_augmented_prompt_async,
    load_session_recap,
    log_augmented_turn,
)
from .config import PrototypeSettings
from .knowledge_store import KnowledgeStore
from .session import PrototypeContext, SessionManager


@dataclass(slots=True)
class PlanPreview:
    plan_result: RunResult
    digest: str


@dataclass(slots=True)
class AugmentationPreview:
    original: str
    suggestion: str
    final_prompt: str
    justification: List[str]
    diff_original_suggestion: str
    diff_original_final: str
    raw_model_response: str


@dataclass(slots=True)
class PrototypeRun:
    task_result: RunResult
    knowledge_exchange_result: Optional[RunResult]
    digest: str
    augmentation: Optional[AugmentationPreview]


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

        original_question = question
        question_for_agent = question
        augmentation_result: Optional[AugmentationResult] = None
        augmentation_task: Optional[asyncio.Task[AugmentationResult]] = None
        recap: Optional[SessionRecap] = None

        if learn_mode:
            recap = load_session_recap(self.knowledge_store, session_id)
            if self.settings.has_api_key:
                augmentation_task = asyncio.create_task(
                    generate_augmented_prompt_async(
                        original_question,
                        recap,
                        model=self.settings.default_model,
                    )
                )
            else:
                augmentation_result = AugmentationResult(
                    rewritten_prompt=original_question,
                    justification=["Augmentation skipped: no API key configured"],
                    raw_text="",
                )

        context = PrototypeContext(
            session_id=session_id,
            knowledge_store=self.knowledge_store,
            learn_mode=learn_mode,
            previous_learnings=[digest],
        )

        if augmentation_task is not None:
            augmentation_result = await augmentation_task
        if augmentation_result is not None:
            question_for_agent = augmentation_result.rewritten_prompt

        task_prompt_parts = [
            f"Session: {session_id}",
            digest,
            "User request:",
            question_for_agent,
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
                    " Use your tools to (1) log the final prompt that went to the task agent,"
                    " (2) log the task output, (3) write a distilled learning with actionable next steps." \
                    f"\n\nOriginal user request:\n{original_question}\n\nFinal prompt sent to task agent:\n{question_for_agent}\n\nTask agent output:\n{task_result.final_output}"
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

        augmentation_preview: Optional[AugmentationPreview] = None
        augmentation = augmentation_result
        augmentation_preview: Optional[AugmentationPreview] = None

        if learn_mode and augmentation is not None:
            suggestion_diff = diff_prompts(original_question, augmentation.rewritten_prompt)
            final_diff = diff_prompts(original_question, question_for_agent)
            log_augmented_turn(
                self.knowledge_store,
                session_id,
                original=original_question,
                suggestion=augmentation.rewritten_prompt,
                final_prompt=question_for_agent,
                suggestion_diff=suggestion_diff,
                final_diff=final_diff,
                justification=augmentation.justification,
                accepted=True,
            )
            augmentation_preview = AugmentationPreview(
                original=original_question,
                suggestion=augmentation.rewritten_prompt,
                final_prompt=question_for_agent,
                justification=augmentation.justification,
                diff_original_suggestion=suggestion_diff,
                diff_original_final=final_diff,
                raw_model_response=augmentation.raw_text,
            )

        return PrototypeRun(
            task_result=task_result,
            knowledge_exchange_result=ke_result,
            digest=digest,
            augmentation=augmentation_preview,
        )


__all__ = ["PrototypeOrchestrator", "PrototypeRun", "PlanPreview", "AugmentationPreview"]
