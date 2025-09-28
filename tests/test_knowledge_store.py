from pathlib import Path

from app.knowledge_store import KnowledgeStore


def test_log_and_retrieve(tmp_path: Path) -> None:
    store = KnowledgeStore(tmp_path)
    store.log("session", "user_actions", "Asked about useEffect", metadata={"summary": "React useEffect intro"})
    digest = store.render_digest("session")
    assert "user_actions" in digest
    entries = store.entries("session")
    assert entries and entries[0].kind == "user_actions"
