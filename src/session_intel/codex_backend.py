"""Bridge for talking to the real Codex CLI via subprocess calls."""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class CodexError(RuntimeError):
    """Raised when invoking the Codex CLI fails."""

    def __init__(self, message: str, *, stdout: str = "", stderr: str = "") -> None:
        super().__init__(message)
        self.stdout = stdout
        self.stderr = stderr


@dataclass
class CodexCliSession:
    """Maintains a Codex CLI session using `codex exec --experimental-json`."""

    workdir: Path
    config_overrides: List[str] = field(default_factory=list)
    env: Optional[Dict[str, str]] = None
    session_id: Optional[str] = None

    def send(self, prompt: str) -> Tuple[str, List[str]]:
        """Send a prompt to Codex, returning assistant text and reasoning lines."""

        base_cmd: List[str] = ["codex", "exec", "--experimental-json"]
        if self.config_overrides:
            base_cmd.extend(self.config_overrides)

        if self.session_id is None:
            cmd = [*base_cmd, prompt]
        else:
            cmd = [*base_cmd, "resume", self.session_id, prompt]

        try:
            completed = subprocess.run(
                cmd,
                cwd=self.workdir,
                env=self.env,
                capture_output=True,
                text=True,
                check=False,
            )
        except FileNotFoundError as exc:  # pragma: no cover - defensive
            raise CodexError("Codex CLI binary not found. Is it installed?") from exc

        stdout = completed.stdout
        stderr = completed.stderr

        if completed.returncode != 0:
            raise CodexError(
                f"Codex CLI returned exit code {completed.returncode}",
                stdout=stdout,
                stderr=stderr,
            )

        if not stdout.strip():  # pragma: no cover - unexpected but guard anyway
            return "(no response)", []

        assistant_chunks: List[str] = []
        reasoning_chunks: List[str] = []

        for line in stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                # Some experimental builds may emit banner text; surface it as part of the answer.
                assistant_chunks.append(line)
                continue

            event_type = payload.get("type")
            if event_type == "session.created":
                self.session_id = payload.get("session_id", self.session_id)
            elif event_type == "item.completed":
                item = payload.get("item", {})
                item_type = item.get("item_type")
                text = item.get("text", "").strip()
                if not text:
                    continue
                if item_type == "assistant_message":
                    assistant_chunks.append(text)
                elif item_type == "reasoning":
                    reasoning_chunks.append(text)
            elif event_type == "response.error":
                message = payload.get("error", {}).get("message", "Unknown Codex error")
                raise CodexError(message, stdout=stdout, stderr=stderr)

        assistant_text = "\n\n".join(chunk for chunk in assistant_chunks if chunk).strip()
        reasoning_texts = [chunk for chunk in reasoning_chunks if chunk]

        return assistant_text or "(no response)", reasoning_texts


__all__ = ["CodexCliSession", "CodexError"]
