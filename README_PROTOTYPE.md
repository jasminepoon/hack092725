# Hack092725 Agents Prototype

This prototype wires the guidance in `AGENTS.md` into a runnable two-agent workflow using the [OpenAI Agents SDK](https://openai.github.io/openai-agents-python/). The system combines a Task Agent that interacts with the human and a Knowledge Exchange (KE) Agent that captures learnings into flat files for reuse.

## Features
- **Task Agent** — answers questions, always reviews recent learnings, and closes with “Next steps”.
- **Knowledge Exchange Agent** — logs the latest user request, the Task Agent output, and a synthesised learning.
- **Flat-file document store** — data lands in `documents/<session_id>/` as JSON-formatted markdown snapshots.
- **Persistent memory** — backed by `agents.SQLiteSession`, so each session accumulates history automatically.
- **Guardrails** — lightweight input scope guard + output quality nudge.
- **Tracing & usage hooks** — rely on the SDK defaults; set `HACK092725_WORKFLOW_NAME` to label traces.

## Prerequisites
- Python 3.10+
- [uv](https://docs.astral.sh/uv/getting-started/installation/) for dependency management
- An `OPENAI_API_KEY` exported in your environment or stored in `.env`

## Quick start
```bash
# Install dependencies
uv pip install .

# (Optional) install dev tooling
uv pip install .[dev]

# Run the CLI (supply a question or wait for the prompt)
OPENAI_API_KEY="sk-..." hack092725-agents --session react-notes "How do I use useEffect for cleanup?"

# Toggle learn mode for a repeated question
hack092725-agents --session react-notes --learn-mode "Remind me about useEffect cleanup patterns"
```

Notes:
- The CLI stores knowledge files in `documents/` by default. Override with `HACK092725_DATA_ROOT`.
- `--learn-mode` surfaces past learnings and asks for confirmation before reusing them.
- `--skip-synthesis` bypasses the KE agent if you just want to inspect Task Agent behaviour.

## Project layout
```
app/
  agents.py              # Task + KE agent factories
  cli.py                 # CLI entrypoint (installed as `hack092725-agents`)
  config.py              # Environment + settings helpers
  guardrails.py          # Input/output guardrails
  knowledge_store.py     # Flat-file document store utilities
  orchestrator.py        # High-level orchestration of agents
  session.py             # Session manager & tool context dataclass
  tools.py               # Function tools exposed to agents

README_PROTOTYPE.md      # This file
AGENTS.md                # Human-facing playbook
pyproject.toml           # uv + project metadata
```

## Testing
```bash
uv pip install .[dev]
pytest
```

## Extending the prototype
1. **Add tools** — extend `app/tools.py` with additional function tools (e.g., repository lookup) and add them to the Task agent.
2. **Richer learn-mode** — implement a double-pass Task agent call where the user approves a generated plan before execution.
3. **Tracing pipeline** — configure custom trace processors (see `tracing` docs) to mirror traces to your observability stack.
4. **Visualization** — install the `viz` extra and run `draw_graph` against the Task agent to inspect the network.

## Troubleshooting
- Ensure the `OPENAI_API_KEY` has access to the models referenced in `pyproject.toml` (defaults to `gpt-4.1`).
- Guardrails raising `InputGuardrailTripwireTriggered` indicates the request hit a scope check; adjust `BANNED_TOPICS` in `guardrails.py` if needed.
- If you run without an API key, the CLI will warn and requests will fail once the agent hits the OpenAI API.
