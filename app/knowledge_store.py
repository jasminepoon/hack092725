"""Flat-file knowledge store used by the Knowledge Exchange agent."""
from __future__ import annotations

import datetime as dt
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional


@dataclass(slots=True)
class KnowledgeEntry:
    session_id: str
    kind: str
    path: Path
    content: str
    metadata: dict


@dataclass(slots=True)
class SessionSnapshotEntry:
    kind: str
    summary: str


@dataclass(slots=True)
class SessionSnapshot:
    session_id: str
    updated_at: dt.datetime
    digest: str
    recent: List[SessionSnapshotEntry]


class KnowledgeStore:
    """Persist structured notes as flat files on disk."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self._digest_cache: dict[str, str] = {}
        self._entries_cache: dict[tuple[str, Optional[str], int], list[KnowledgeEntry]] = {}
        self._session_cache: dict[str, SessionSnapshot] = {}

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

        self._invalidate_caches(session_id)

        return KnowledgeEntry(
            session_id=session_id,
            kind=kind,
            path=path,
            content=content,
            metadata=metadata or {},
        )

    def _invalidate_caches(self, session_id: str) -> None:
        self._digest_cache.pop(session_id, None)
        keys_to_remove = [key for key in self._entries_cache if key[0] == session_id]
        for key in keys_to_remove:
            self._entries_cache.pop(key, None)
        self._session_cache.pop(session_id, None)

    def entries(self, session_id: str, kind: Optional[str] = None, limit: int = 5) -> list[KnowledgeEntry]:
        """Return up to ``limit`` entries for the session (newest first)."""

        cache_key = (session_id, kind, limit)
        if cache_key in self._entries_cache:
            return list(self._entries_cache[cache_key])

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
        self._entries_cache[cache_key] = list(results)
        return results

    def render_digest(self, session_id: str, limit: int = 3) -> str:
        """Return a human-readable digest of recent learnings."""

        if session_id in self._digest_cache:
            return self._digest_cache[session_id]

        entries = self.entries(session_id, limit=limit)
        if not entries:
            return "No previous learnings recorded."

        lines: list[str] = ["Recent learnings:"]
        for entry in entries:
            summary = entry.metadata.get("summary") or entry.content.splitlines()[0].strip()
            lines.append(f"- [{entry.kind}] {summary}")
        digest = "\n".join(lines)
        self._digest_cache[session_id] = digest
        return digest

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

    def list_sessions(self, limit: int = 20) -> list[SessionSnapshot]:
        """Return the most recently updated sessions with lightweight metadata."""

        if not self.root.exists():
            return []

        snapshots: list[SessionSnapshot] = []
        for session_dir in self.root.iterdir():
            if not session_dir.is_dir():
                continue

            session_id = session_dir.name
            cached = self._session_cache.get(session_id)
            if cached is not None:
                snapshots.append(cached)
                continue
            files = sorted(session_dir.glob("*"), key=lambda p: p.stat().st_mtime, reverse=True)
            if files:
                updated_ts = files[0].stat().st_mtime
            else:
                updated_ts = session_dir.stat().st_mtime
            updated_at = dt.datetime.fromtimestamp(updated_ts, tz=dt.timezone.utc)

            digest = self.render_digest(session_id)

            recent_entries = self.entries(session_id, limit=5)
            recent = [
                SessionSnapshotEntry(
                    kind=entry.kind,
                    summary=(entry.metadata.get("summary") or entry.content.splitlines()[0][:160]).strip(),
                )
                for entry in recent_entries
            ]

            snapshot = SessionSnapshot(
                session_id=session_id,
                updated_at=updated_at,
                digest=digest,
                recent=recent,
            )
            self._session_cache[session_id] = snapshot
            snapshots.append(snapshot)

        snapshots.sort(key=lambda item: item.updated_at, reverse=True)
        return snapshots[:limit]


__all__ = [
    "KnowledgeStore",
    "KnowledgeEntry",
    "SessionSnapshot",
    "SessionSnapshotEntry",
]
