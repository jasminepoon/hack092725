"""Flat-file knowledge store used by the Knowledge Exchange agent."""
from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional


@dataclass(slots=True)
class KnowledgeEntry:
    session_id: str
    kind: str
    path: Path
    content: str
    metadata: dict


class KnowledgeStore:
    """Persist structured notes as flat files on disk."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def _session_dir(self, session_id: str) -> Path:
        return self.root / session_id

    def log(self, session_id: str, kind: str, content: str, metadata: Optional[dict] = None) -> KnowledgeEntry:
        """Write a new entry and return the resulting record."""

        session_dir = self._session_dir(session_id)
        session_dir.mkdir(parents=True, exist_ok=True)
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        suffix = metadata.get("suffix") if metadata else None
        filename = f"{timestamp}-{kind}{('-' + suffix) if suffix else ''}.md"
        path = session_dir / filename

        payload = {
            "kind": kind,
            "metadata": metadata or {},
            "content": content,
        }
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

        return KnowledgeEntry(
            session_id=session_id,
            kind=kind,
            path=path,
            content=content,
            metadata=metadata or {},
        )

    def entries(self, session_id: str, kind: Optional[str] = None, limit: int = 5) -> list[KnowledgeEntry]:
        """Return up to ``limit`` entries for the session (newest first)."""

        session_dir = self._session_dir(session_id)
        if not session_dir.exists():
            return []

        files = sorted(session_dir.glob("*.md"), reverse=True)
        results: list[KnowledgeEntry] = []
        for path in files:
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            entry_kind = payload.get("kind", "unknown")
            if kind and entry_kind != kind:
                continue
            results.append(
                KnowledgeEntry(
                    session_id=session_id,
                    kind=entry_kind,
                    path=path,
                    content=payload.get("content", ""),
                    metadata=payload.get("metadata", {}),
                )
            )
            if len(results) >= limit:
                break
        return results

    def render_digest(self, session_id: str, limit: int = 3) -> str:
        """Return a human-readable digest of recent learnings."""

        entries = self.entries(session_id, limit=limit)
        if not entries:
            return "No previous learnings recorded."

        lines: list[str] = ["Recent learnings:"]
        for entry in entries:
            summary = entry.metadata.get("summary") or entry.content.splitlines()[0].strip()
            lines.append(f"- [{entry.kind}] {summary}")
        return "\n".join(lines)

    def iter_all(self, session_id: str) -> Iterable[KnowledgeEntry]:
        """Iterate over every entry for a session (oldest first)."""

        session_dir = self._session_dir(session_id)
        if not session_dir.exists():
            return []
        return (
            KnowledgeEntry(
                session_id=session_id,
                kind=payload.get("kind", "unknown"),
                path=path,
                content=payload.get("content", ""),
                metadata=payload.get("metadata", {}),
            )
            for path in sorted(session_dir.glob("*.md"))
            for payload in [json.loads(path.read_text(encoding="utf-8"))]
        )


__all__ = ["KnowledgeStore", "KnowledgeEntry"]
