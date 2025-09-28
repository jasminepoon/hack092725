"""Configuration helpers for the Hack092725 Agents prototype."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

from agents import set_tracing_disabled


@dataclass(slots=True)
class PrototypeSettings:
    """Centralised runtime configuration."""

    openai_api_key: Optional[str]
    default_model: str
    workflow_name: str
    data_root: Path
    session_db: Path

    @property
    def has_api_key(self) -> bool:
        return bool(self.openai_api_key)


def load_settings(env_path: Optional[Path] = None) -> PrototypeSettings:
    """Load settings from the environment (optionally using a .env file)."""

    if env_path is None:
        # Honour a top-level .env if present; otherwise rely on process env vars.
        env_path = Path(".env")
    if env_path.exists():
        load_dotenv(env_path)

    if os.getenv("HACK092725_ENABLE_TRACING") != "1":
        set_tracing_disabled(True)

    root = Path(os.getenv("HACK092725_DATA_ROOT", "documents")).resolve()
    root.mkdir(parents=True, exist_ok=True)

    session_db = root / "sessions.sqlite"

    return PrototypeSettings(
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        default_model=os.getenv("OPENAI_DEFAULT_MODEL", "gpt-4.1"),
        workflow_name=os.getenv("HACK092725_WORKFLOW_NAME", "Hack092725 Prototype"),
        data_root=root,
        session_db=session_db,
    )


__all__ = ["PrototypeSettings", "load_settings"]
