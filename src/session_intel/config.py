"""Configuration constants for the Session Intelligence prototype."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables from .env if present so dogfooding is painless.
load_dotenv()

# Root folder where session artifacts live.
DOCUMENTS_ROOT = Path(os.environ.get("SESSION_INTEL_DOCUMENTS_ROOT", "documents"))

# Shared SQLite database for OpenAI Agents SDK session memory.
SQLITE_DB_PATH = DOCUMENTS_ROOT / "sessions.db"

# Default GPT model for summarisation/augmentation.
# Default to a generally available model; override via SESSION_INTEL_MODEL if needed.
DEFAULT_MODEL = os.environ.get("SESSION_INTEL_MODEL", "gpt-4o-mini")

# Markdown template header
LEARNINGS_HEADER_TEMPLATE = "# Session {session_id} — {timestamp}\n\n## Turn Log\n"

# Summary section header appended at the end of a session
SUMMARY_HEADER = "\n## Session Summary\n"
