# MVP Tickets: Session Memory Prototype

> Lean implementation that reuses ideas from `session_memory.ipynb`. Split into first-pass (gap capture) and second-pass (learn mode) increments. Every ticket includes a lightweight Definition of Done (DoD).

## First-Pass (Gap Capture Mode)

### Ticket FP1 – Minimal Session Memory Wiring
- **Goal:** Use OpenAI Agents SDK `SQLiteSession` to persist multi-turn dialogue without any custom summarization.
- **Scope:** Instantiate `SQLiteSession(session_id, db_path)` inside the orchestrator using a shared database at `documents/sessions.db`. Expose helper functions to create/resume sessions and ensure the file lives alongside other documents.
- **DoD:**
  - Session IDs logged alongside timestamps.
  - Consecutive calls to the task agent reflect prior turns when listing `await session.get_items()`.
  - Unit smoke test shows session history survives process restart via the shared SQLite file.

### Ticket FP2 – Knowledge Exchange (KE) Logging Skeleton
- **Goal:** Mirror notebook’s `session.add_items` usage by emitting structured records to disk for humans.
- **Scope:** Implement KE agent module that subscribes to turn events (user message, assistant reply, tool action) and appends them to three files (`user_actions.jsonl`, `agent_actions.jsonl`, `learnings.md`) stored under `documents/<session_id>/`. No summarization yet; just raw dump with metadata (`role`, `content`, `turn`, `timestamp`).
- **DoD:**
  - After any turn, the three documents update without manual refresh.
  - `learnings.md` contains a heading for the session and at least one bullet per turn (can be verbatim for now).
  - Files stored within `documents/<session_id>/` directory for easy retrieval.

### Ticket FP3 – Last-N Turn Trimming Toggle
- **Goal:** Reproduce the notebook’s “context trimming” with `TrimmingSession` (or manual wrapper) to keep the last `N` real user turns.
- **Scope:** Add configuration `context_limit` & `keep_last_n_turns`. Wrap `session.add_items` so that once `context_limit` is exceeded, older turns are pruned (no summarizer yet) while the KE logs remain complete.
- **DoD:**
  - Config defaults: `context_limit=6`, `keep_last_n_turns=3`.
  - Logging shows older turns removed from session memory, while KE files still preserve the full raw log.
  - Simple regression script prints token count before/after trimming.

### Ticket FP4 – End-of-Session Synthesis
- **Goal:** Lightweight summarizer call (one GPT prompt) that mimics `SummarizingSession` output to populate `learnings.md` with gaps + next reps.
- **Scope:** On session close, send final turn batch to GPT‑5 (single call) asking for: timeline highlights, unresolved questions, suggested next steps. Append to the markdown under `## Session Summary`.
- **DoD:**
  - `learnings.md` ends with summary section containing three bullet groups.
  - Summary call is optional (skip when `OPENAI_API_KEY` missing) but the pipeline still completes.
  - Manual inspection confirms user gaps captured from latest turns.

## Second-Pass (Learn Mode)

### Ticket SP1 – Session Resume & Knowledge Retrieval
- **Goal:** When “learn mode” flag is true, preload the latest session artifacts and show them in the UI/CLI before accepting new questions.
- **Scope:** Implement `load_previous_session(session_id)` to grab most recent `learnings.md` entry + last five user actions. Render them to the human (stdout / UI panel) before prompting and inject the same recap into the task agent context as a system preface.
- **DoD:**
  - CLI command `resume_session <id>` prints recap and outstanding gaps.
  - Task agent receives the recap in its system prompt (read-only, no rewrite yet).
  - Works even if summary missing (falls back to raw actions list).
- **Status (2025-09-28):** Implemented in `scripts/run_learn_mode.py` using `load_session_recap()`; recap prints to CLI and feeds the task agent system instructions.

### Ticket SP2 – KE Message Augmentation (Core Feature)
- **Goal:** Knowledge Exchange agent rewrites/augments user’s incoming message before it hits the task agent, and produces that same augmented message for the human as markdown (per PDF guidance).
- **Scope:**
  - Combine original question + relevant snippets from `learnings.md` into a new message using GPT‑5.
  - Mirror the optimization mechanism from `prompt-optimization-cookbook.ipynb`: append or overwrite the user turn with the augmented version before sending to the task agent.
  - Store augmented prompt in `documents/<session_id>/augmented_turns.md` (human-readable). Allow human to view/edit the augmented text before final send (simple Y/N prompt or UI toggle).
- **DoD:**
  - Every learn-mode turn saves an entry showing **Original**, **Augmented for Task Agent**, **What changed** (diff/highlight).
  - Task agent logs confirm it received the augmented form (compare with previous raw version).
  - Human confirmation workflow tested for both accept and edit paths.
- **Status (2025-09-28):** Learn-mode CLI previews suggested rewrites, logs to `augmented_turns.md`, and records whether the human accepted or edited the prompt.

### Ticket SP3 – Background Logger Enhancements
- **Goal:** Extend background/log component to capture how the task agent executed the plan, closing the loop for “constant logging + refresh”.
- **Scope:**
  - Record tool calls, code edits, and status messages into `agent_actions.jsonl` with extra metadata (`tool`, `args`, `result_snippet`).
  - Trigger KE agent to immediately reflect critical updates back into `learnings.md` (e.g., mark hook gap as resolved).
- **DoD:**
  - After augmented prompt runs, logs show the corresponding execution trail within 1s.
  - Markdown reflects status change (e.g., `Hooks gap – resolved on 2025-01-06`).
  - No duplicate log entries across repeated polling cycles.

### Ticket SP4 – Learn Mode Exit Criteria
- **Goal:** Provide a lean mechanism to decide when learn mode can be toggled off (e.g., once gaps marked resolved or after N successful turns).
- **Scope:** Implement tiny rule engine: if all gaps in latest summary labeled “resolved” OR user answers `done`, system switches back to first-pass mode automatically.
- **DoD:**
  - Unit test: simulate session with gap resolution -> learn mode flips to false.
  - UI/CLI message tells user why learn mode switched off.
  - State persisted so next session start respects the new mode.

## Decisions (resolved from earlier questions)
- Shared SQLite database lives at `documents/sessions.db`.
- GPT‑5 is the default model for summarization and augmentation calls.
- No additional compliance constraints for storing code/tool traces.
- Augmented prompts replace or append the user message sent to the task agent, following the prompt optimization cookbook pattern.

*Let me know if anything else needs to be tweaked.*
