# hack092725 - agent rules but for people

Early prototype for capturing developer learning during AI-assisted coding sessions.

## Step-by-Step User Guide

1. **Check prerequisites**
   - macOS or Linux with Python 3.9+ available on `PATH`.
   - Access to the OpenAI API (key with GPT-4o/GPT-5 tier enabled).
   - OpenAI Codex CLI installed (`codex --version` should work). The direct-embed flows shell out to the real Codex binary via `codex exec --experimental-json`.
   - Git checkout of this repo (e.g. `git clone ... && cd hack092725`).
2. **Create + activate a virtual environment**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
   > The CLI bootstraps `.venv` automatically, but activating keeps tooling consistent.
3. **Install dependencies**
   ```bash
   python -m pip install --upgrade pip
   pip install --force-reinstall --no-cache-dir -r requirements.txt
   ```
   Re-run this step if you ever see `ModuleNotFoundError: pydantic_core._pydantic_core`.
4. **Provide your API key**
   - Either export it for the current shell: `export OPENAI_API_KEY=sk-...`
   - Or add it to a local `.env` file in the repo root (`OPENAI_API_KEY="sk-..."`). The scripts auto-load `.env` via `python-dotenv`.
5. **Run the first-pass session logger**
   ```bash
   .venv/bin/python scripts/run_codex_cli.py --mode first-pass
   ```
   - Type natural-language questions; the agent responds inline.
   - Enter `:exit` (or press `Ctrl+D`) to finish and trigger the summary.
   - Artifacts appear under `documents/<session_id>/` (`learnings.md`, `user_actions.jsonl`, `agent_actions.jsonl`).
   - Each run also records the underlying Codex session id in `codex_session_id.txt`, so you can resume directly with `codex exec resume <id> ...` if needed.
6. **Review the captured learnings**
   - Open `documents/<session_id>/learnings.md` to read the turn log and auto-generated summary.
   - Keep these notes handy for future sessions or share them with teammates.
7. **Switch to learn mode when ready**
   ```bash
   .venv/bin/python scripts/run_codex_cli.py --mode learn [--source-session <previous_session_id>]
   ```
   - The CLI prints the prior summary, recent turn bullets, and latest user questions.
   - For each new turn, it previews a Knowledge Exchange rewrite. Choose `y` to accept, `n` to send your original, or `e` to edit.
   - The chosen prompt is sent to the task agent; responses and summaries continue to log to the session folder.
8. **Inspect augmented prompts**
   - Check `documents/<session_id>/augmented_turns.md` to compare the original request, suggested rewrite, final text sent, justification bullets, and whether you accepted the augmentation.
9. **Wrap up + hand off**
   - On `:exit`, a fresh summary is appended to `learnings.md`.
   - Share the entire `documents/<session_id>/` folder or the markdown files with collaborators for quick onboarding.
   - Legacy scripts (`scripts/run_first_pass.py`, `scripts/run_learn_mode.py`) remain available if you want to exercise the individual flows directly.

## Codex CLI Integration Details

These prototypes now run *through* the official Codex binary instead of the Agents SDK. Here is what to expect and how to operate it safely:

- **How prompts flow**
  - The first turn sent to Codex is prefixed with the instruction bundle from previous learnings, so the task agent starts with the recap in-context.
  - In learn mode the Knowledge Exchange agent previews a rewrite before anything hits Codex; you decide whether to send the augmentation, keep the original, or edit inline.

- **Running the bridged CLI**
  ```bash
  # First-pass capture
  .venv/bin/python scripts/run_codex_cli.py --mode first-pass

  # Learn mode with recap from the latest session (or pick one via --source-session)
  .venv/bin/python scripts/run_codex_cli.py --mode learn
  .venv/bin/python scripts/run_codex_cli.py --mode learn --source-session <session_id>
  ```

- **Resuming in native Codex**
  - Each run captures the underlying Codex session id at `documents/<session_id>/codex_session_id.txt`.
  - Resume that conversation directly with:
    ```bash
    codex exec resume $(cat documents/<session_id>/codex_session_id.txt) "<follow-up prompt>"
    ```

- **Troubleshooting**
  - If you ever see `ModuleNotFoundError: pydantic_core._pydantic_core`, reinstall with `.venv/bin/pip install --force-reinstall --no-cache-dir -r requirements.txt` (arm64 wheels are required for Codex’s agent deps).
  - A `Codex CLI returned exit code ...` message usually means the binary could not authenticate; ensure `codex login` has been run and that your OpenAI API key is set.
  - Long Codex calls now emit heartbeat logs (`... still waiting on Codex (45s elapsed)`) every 15 seconds so you know the request is still live; the total runtime prints once the response arrives.
  - The CLI prints `(thinking) ...` lines when Codex emits reasoning events; these are logged so you can study the model’s chain-of-thought later inside `documents/<session_id>/agent_actions.jsonl`.

- **Artifacts to expect**
  - `learnings.md` – running turn log, summaries, and session-level highlights.
  - `augmented_turns.md` – available in learn mode, capturing original vs. rewritten prompts plus justification.
  - `codex_session_id.txt` – the Codex-side session identifier for future resumes or raw Codex dogfooding.

## First-Pass (Gap Capture) Prototype

1. **Install dependencies**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   python -m pip install --upgrade pip
   pip install --force-reinstall --no-cache-dir -r requirements.txt
   ```
2. **Set your API key** (required for agent replies + summaries)
   - Either export it manually:
     ```bash
     export OPENAI_API_KEY=sk-...
     ```
   - Or drop it into a local `.env` file (`OPENAI_API_KEY="sk-..."`). The tool
     now auto-loads `.env` on startup via `python-dotenv` so you don’t have to
     export it for each shell.
3. **Run the interactive loop**
   ```bash
   python scripts/run_first_pass.py
   ```
   - Use `--session-id <id>` to resume a previous run.
   - Type `:exit` to finish the session and trigger the GPT-5 summary.
   > Tip: the script auto-detects `.venv` even if you forget to `source` it, but
   > activating keeps imports and tooling consistent. If you see a
   > `pydantic-core` error, rerun the install step above.

Artifacts are stored under `documents/`:
- `sessions.db` – shared SQLite memory used by the OpenAI Agents SDK.
- `documents/<session_id>/user_actions.jsonl` – raw user turns.
- `documents/<session_id>/agent_actions.jsonl` – assistant outputs/tool traces.
- `documents/<session_id>/learnings.md` – running turn log plus end-of-session summary.

These files power the Knowledge Exchange agent in later passes and give humans a quick journal of what happened, what was confusing, and what to revisit next.

## Second-Pass (Learn Mode) Prototype

1. **Prep**
   - Complete the first-pass install steps above (same virtualenv and requirements).
   - Ensure you have at least one prior session folder under `documents/` so the recap has something to load.
2. **Run the learn-mode loop**
   ```bash
   python scripts/run_learn_mode.py [--source-session <id>] [--session-id <new-id>]
   ```
   - Defaults to the latest session directory for context if `--source-session` is omitted.
   - The CLI prints the previous summary + recent turns, then previews the Knowledge Exchange rewrite for each new message.
   - Respond with `y`/`n`/`e` to accept, reject, or edit the augmented prompt before it hits the task agent.
3. **Artifacts**
   - `documents/<session_id>/augmented_turns.md` – captures original prompt, suggested rewrite, final text sent, justification, and whether the human accepted it.
   - Other files mirror first-pass behaviour (raw JSONL logs + updated `learnings.md` with a fresh summary on exit).
