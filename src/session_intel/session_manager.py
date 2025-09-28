"""Utilities for creating/resuming OpenAI Agents SDK sessions."""

from __future__ import annotations

import datetime as dt
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from agents import SQLiteSession  # type: ignore

from .config import DOCUMENTS_ROOT, SQLITE_DB_PATH


@dataclass
class SessionContext:
    """Bundle of metadata we carry around for each active session."""

    session_id: str
    session: SQLiteSession
    created_at: dt.datetime
    documents_dir: Path


def _ensure_documents_root() -> None:
    DOCUMENTS_ROOT.mkdir(parents=True, exist_ok=True)


def _ensure_session_dir(session_id: str) -> Path:
    """Ensure the per-session directory exists and return it."""

    session_dir = DOCUMENTS_ROOT / session_id
    session_dir.mkdir(parents=True, exist_ok=True)
    return session_dir


def create_session(session_id: Optional[str] = None) -> SessionContext:
    """Create a fresh session (or resume if id provided)."""

    _ensure_documents_root()

    if session_id is None:
        session_id = dt.datetime.utcnow().strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:6]

    documents_dir = _ensure_session_dir(session_id)

    sqlite_session = SQLiteSession(session_id=session_id, db_path=str(SQLITE_DB_PATH))

    return SessionContext(
        session_id=session_id,
        session=sqlite_session,
        created_at=dt.datetime.utcnow(),
        documents_dir=documents_dir,
    )
