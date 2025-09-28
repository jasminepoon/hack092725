"""Session and context utilities for the prototype."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional

from agents import SQLiteSession

from .knowledge_store import KnowledgeStore


@dataclass(slots=True)
class PrototypeContext:
    """Context object passed to tools and agents via RunContextWrapper."""

    session_id: str
    knowledge_store: KnowledgeStore
    learn_mode: bool = False
    previous_learnings: list[str] = field(default_factory=list)


class SessionManager:
    """Lazily manages SQLite-backed sessions."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._sessions: Dict[str, SQLiteSession] = {}

    def get(self, session_id: str) -> SQLiteSession:
        """Return a cached SQLiteSession for the given session id."""

        if session_id not in self._sessions:
            self._sessions[session_id] = SQLiteSession(session_id, str(self._db_path))
        return self._sessions[session_id]

    async def close_all(self) -> None:
        """Dispose of open sessions (best-effort)."""

        tasks = []
        for session in self._sessions.values():
            maybe = session.close()
            if asyncio.iscoroutine(maybe) or isinstance(maybe, asyncio.Future):
                tasks.append(maybe)
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        self._sessions.clear()


__all__ = ["PrototypeContext", "SessionManager"]
