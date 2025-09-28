"""Integration-style tests for the FastAPI wrapper."""
from __future__ import annotations

import datetime as dt
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

import app.api as api
from app.orchestrator import AugmentationPreview, PlanPreview, PrototypeRun
from app.knowledge_store import SessionSnapshot, SessionSnapshotEntry


def _build_usage() -> SimpleNamespace:
    return SimpleNamespace(
        requests=1,
        input_tokens=123,
        output_tokens=456,
        total_tokens=579,
    )


def _build_guardrail_result(message: str) -> SimpleNamespace:
    return SimpleNamespace(output=SimpleNamespace(output_info=message))


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    async def fake_plan(session_id: str, question: str) -> PlanPreview:  # noqa: ARG001 - parity with real impl
        plan_result = SimpleNamespace(final_output="### Plan\n- step 1")
        return PlanPreview(plan_result=plan_result, digest="Session digest stub")

    async def fake_run(
        session_id: str,
        question: str,
        *,
        learn_mode: bool,
        synthesise_learning: bool,
    ) -> PrototypeRun:  # noqa: ARG001
        task_result = SimpleNamespace(
            final_output="Task agent answer",
            output_guardrail_results=[_build_guardrail_result("Guardrail ok")],
            context_wrapper=SimpleNamespace(usage=_build_usage()),
        )
        ke_result = SimpleNamespace(final_output="KE summary")
        augmentation = AugmentationPreview(
            original="Original question",
            suggestion="Augmented suggestion",
            final_prompt="Augmented suggestion",
            justification=["Reused prior learning"],
            diff_original_suggestion="- old\n+ new",
            diff_original_final="- old\n+ new",
            raw_model_response="{\n  'rewritten_prompt': 'Augmented suggestion'\n}",
        )
        return PrototypeRun(
            task_result=task_result,
            knowledge_exchange_result=ke_result,
            digest="Session digest stub",
            augmentation=augmentation,
        )

    monkeypatch.setattr(api._orchestrator, "build_learn_mode_plan", fake_plan)
    monkeypatch.setattr(api._orchestrator, "run_turn", fake_run)
    monkeypatch.setattr(
        api._knowledge_store,
        "list_sessions",
        lambda limit=20: [
            SessionSnapshot(
                session_id="demo",
                updated_at=dt.datetime(2025, 1, 1, tzinfo=dt.timezone.utc),
                digest="Recent learnings:\n- (user_actions) Asked about taxes",
                recent=[SessionSnapshotEntry(kind="user_actions", summary="Asked about taxes")],
            )
        ],
    )

    return TestClient(api.app)


def test_plan_endpoint_returns_preview(client: TestClient) -> None:
    response = client.post(
        "/plan",
        json={"session_id": "demo", "question": "How do we deploy?"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["plan_markdown"].startswith("### Plan")
    assert payload["digest"] == "Session digest stub"


def test_run_endpoint_surfaces_augmentation(client: TestClient) -> None:
    response = client.post(
        "/run",
        json={
            "session_id": "demo",
            "question": "Do you remember my tax preferences?",
            "learn_mode": True,
        },
    )

    assert response.status_code == 200
    payload = response.json()

    assert payload["final_output"] == "Task agent answer"
    assert payload["knowledge_exchange_summary"] == "KE summary"
    assert payload["guardrail_feedback"] == ["Guardrail ok"]
    assert payload["usage"] == {
        "requests": 1,
        "input_tokens": 123,
        "output_tokens": 456,
        "total_tokens": 579,
    }

    augmentation = payload["augmentation"]
    assert augmentation["original"] == "Original question"
    assert augmentation["suggestion"] == "Augmented suggestion"
    assert augmentation["diff_original_suggestion"].startswith("- old")
    assert augmentation["justification"] == ["Reused prior learning"]


def test_sessions_endpoint_returns_history(client: TestClient) -> None:
    response = client.get("/sessions?limit=5")

    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload, list) and payload

    first = payload[0]
    assert first["session_id"] == "demo"
    assert first["digest"].startswith("Recent learnings")
    assert first["recent"][0]["kind"] == "user_actions"
