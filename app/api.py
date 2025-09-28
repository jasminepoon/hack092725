"""FastAPI wrapper for running Hack092725 agents."""
from __future__ import annotations

import asyncio
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from .config import load_settings
from .knowledge_store import KnowledgeStore, SessionSnapshot
from .orchestrator import PlanPreview, PrototypeOrchestrator
from .session import SessionManager

app = FastAPI(title="Hack092725 Agents API")

_settings = load_settings()
_session_manager = SessionManager(_settings.session_db)
_knowledge_store = KnowledgeStore(_settings.data_root)
_orchestrator = PrototypeOrchestrator(_settings, _session_manager, _knowledge_store)


class PlanRequest(BaseModel):
    session_id: str
    question: str


class PlanResponse(BaseModel):
    plan_markdown: str
    digest: str


class RunRequest(BaseModel):
    session_id: str
    question: str
    learn_mode: bool = False
    skip_synthesis: bool = False
    extra_guidance: Optional[str] = None


class AugmentationPayload(BaseModel):
    original: str
    suggestion: str
    final_prompt: str
    justification: List[str]
    diff_original_suggestion: str
    diff_original_final: str
    raw_model_response: str


class RunResponse(BaseModel):
    final_output: str
    guardrail_feedback: list[str]
    knowledge_exchange_summary: Optional[str]
    usage: Optional[dict]
    digest: str
    augmentation: Optional[AugmentationPayload]


class SessionSummaryItem(BaseModel):
    kind: str
    summary: str


class SessionSummary(BaseModel):
    session_id: str
    updated_at: str
    digest: str
    recent: List[SessionSummaryItem]


@app.on_event("shutdown")
async def shutdown_event() -> None:
    await _session_manager.close_all()


@app.get("/")
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/plan", response_model=PlanResponse)
async def build_plan(request: PlanRequest) -> PlanResponse:
    preview: PlanPreview = await _orchestrator.build_learn_mode_plan(
        request.session_id,
        request.question,
    )
    return PlanResponse(plan_markdown=preview.plan_result.final_output, digest=preview.digest)


@app.post("/run", response_model=RunResponse)
async def run_agents(request: RunRequest) -> RunResponse:
    question = request.question
    if request.extra_guidance:
        guidance = request.extra_guidance.strip()
        if guidance:
            question = f"{question}\n\nAdditional guidance from user: {guidance}"

    try:
        result = await _orchestrator.run_turn(
            session_id=request.session_id,
            question=question,
            learn_mode=request.learn_mode,
            synthesise_learning=not request.skip_synthesis,
        )
    except Exception as exc:  # pragma: no cover - surface errors to client
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    guardrail_messages: list[str] = []
    if result.task_result.output_guardrail_results:
        for guardrail_result in result.task_result.output_guardrail_results:
            info = getattr(getattr(guardrail_result, "output", None), "output_info", None)
            if info:
                guardrail_messages.append(info)

    ke_summary = result.knowledge_exchange_result.final_output if result.knowledge_exchange_result else None

    usage_data = None
    context_wrapper = getattr(result.task_result, "context_wrapper", None)
    if context_wrapper and context_wrapper.usage:
        usage = context_wrapper.usage
        usage_data = {
            "requests": usage.requests,
            "input_tokens": usage.input_tokens,
            "output_tokens": usage.output_tokens,
            "total_tokens": usage.total_tokens,
        }

    augmentation_payload = None
    if result.augmentation is not None:
        augmentation_payload = AugmentationPayload(
            original=result.augmentation.original,
            suggestion=result.augmentation.suggestion,
            final_prompt=result.augmentation.final_prompt,
            justification=result.augmentation.justification,
            diff_original_suggestion=result.augmentation.diff_original_suggestion,
            diff_original_final=result.augmentation.diff_original_final,
            raw_model_response=result.augmentation.raw_model_response,
        )

    return RunResponse(
        final_output=result.task_result.final_output,
        guardrail_feedback=guardrail_messages,
        knowledge_exchange_summary=ke_summary,
        usage=usage_data,
        digest=result.digest,
        augmentation=augmentation_payload,
    )


@app.get("/sessions", response_model=List[SessionSummary])
async def list_sessions(limit: int = 20) -> List[SessionSummary]:
    snapshots: List[SessionSnapshot] = _knowledge_store.list_sessions(limit=limit)
    return [
        SessionSummary(
            session_id=snapshot.session_id,
            updated_at=snapshot.updated_at.isoformat(),
            digest=snapshot.digest,
            recent=[
                SessionSummaryItem(kind=item.kind, summary=item.summary)
                for item in snapshot.recent
            ],
        )
        for snapshot in snapshots
    ]
