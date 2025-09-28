# Brainstorming: Session Intelligence MVP

## Background
- We want Codex to help developers repeat unfamiliar tasks by remembering prior sessions.
- Today, conversation history, actions, and skill gaps vanish after each session, so users relearn the same steps and Codex lacks continuity.

## Problem Statement
Developers using Codex to accomplish skills outside their expertise (e.g., building a React app as a Python engineer) lose traceability of decisions, gaps, and AI guidance once a session ends. Without a structured record, they struggle to reproduce workflows, improve skills, or let Codex adapt in future sessions.

## Solution Shape
- Capture each session’s dialogue, commands, outcomes, and intent in a structured log.
- Layer metadata that highlights knowledge gaps, decision points, and coaching quality to build a "session intelligence profile."
- Provide replayable timelines plus concise summaries for humans; feed relevant insights back to Codex for future personalization.

## Core Components
- **Session Recorder**: Hooks into conversation + tool usage, normalizes them into an event schema.
- **Insight Engine**: Uses GPT‑5 prompts to tag gaps ("What is `useEffect`?"), confusion, successes, and follow-ups.
- **Artifact Store**: Persists structured logs, summaries, and action plans with versioning/access controls.
- **Review Console**: UI for timelines, key decisions, suggested learning, and reproducible playbooks.
- **Context Injector**: Supplies relevant past insights to Codex when a new session begins.

## Prototype: Sub-Agent Notebook
- Introduce a "notetaker" (Knowledge Exchange agent) beside Codex.
- Each turn it records: what happened, where confusion appeared, and the takeaway for next time.
- Entries append to a human-readable `learnings.md`, using a consistent template (turn ID, action, gap, outcome).
- Periodic lightweight summaries keep the file digestible; older sessions archived on session end.
- Codex and the developer read the latest notes before the next session, aligning on gaps and focus areas.

## Implementation Decisions (Jan 06)
- Shared SQLite session memory lives at `documents/sessions.db`.
- All summarization and augmentation calls use GPT‑5 for consistency.
- Knowledge Exchange agent owns a `documents/<session_id>/` directory containing:
  - `user_actions.jsonl`, `agent_actions.jsonl`, `augmented_turns.md`, and `learnings.md`.
  - Raw turn data is append-only; markdown captures human-facing highlights.
- Background logger streams task-agent tool calls and status updates back into the same document set for “constant logging + refresh.”

## First Pass vs Second Pass
- **First Pass (Gap Capture Mode)**
  - Goal: record everything, identify skill gaps, and synthesize a session summary at close.
  - Mechanics: task agent runs untouched; Knowledge Exchange agent logs user actions, agent actions, and a plain-language per-turn entry in `learnings.md`.
  - End-of-session GPT‑5 summary adds timeline highlights, unresolved questions, and suggested next reps.
- **Second Pass (Learn Mode)**
  - Goal: reuse prior knowledge to move faster and close gaps.
  - Before each turn, Knowledge Exchange agent retrieves the latest summary + relevant snippets and uses GPT‑5 to **augment/overwrite the user message** (mirroring the prompt-optimization cookbook pattern).
  - Augmented prompt is both sent to the task agent and surfaced to the human in `augmented_turns.md`, showing original text, rewritten text, and diff.
  - Human confirms the rewrite (accept/edit) before execution; once the task agent finishes, logs and markdown update in real time.
  - Learn mode exits automatically once all tracked gaps are marked resolved or the user signals completion.

## Happy Path Walkthrough
1. **Session 1 (First Pass)**: Coder + AI build a React site; Knowledge Exchange agent captures each exchange and synthesizes a `learnings.md` entry (timeline, gaps, next reps).
2. **Between Sessions**: Notes and raw logs live in `documents/<session_id>/`; SQLite session memory preserves context for debugging.
3. **Session 2 (Second Pass)**: Developer reviews the latest summary; Knowledge Exchange agent preloads context, rewrites the user message with reminders (“Here’s how we solved it last time”), and the human approves the plan.
4. **Execution**: Task agent executes using the augmented prompt; background logger records tool usage.
5. **Wrap-Up**: Knowledge Exchange agent updates markdown, marks gaps resolved, and suggests new repetitions (e.g., automate deployment).

## Flow Overview
```
+----------------------+      +-----------------------+
| Frontend             |----->| Documents (SQLite +   |
| (session start)      |      | markdown artifacts)   |
+----------+-----------+      +-----------+-----------+
           |                             ^
           v                             |
+----------------------+      constant logging & refresh
| Knowledge Exchange   |-------------------------------+
| agent (GPT-5)        |                               |
+----+-----------+-----+                               |
     |           |                                     |
 data |    augmented prompt                            |
logging|           v                                   |
     v        +-----------+----------------------------+
+------------+| Task Agent|                            |
| Background |+-----------+                            |
| Logger     |     ^                                    
+------------+     |                                    
                   | confirmation                        
                   +------------------------------------>
                 Human user (views original vs augmented prompt)
```

## Open Questions
- Exact schema for each turn (fields, tagging vocabulary, confidence scores?).
- How and when to trigger summaries vs. raw log entries.
- Tooling footprint for the Knowledge Exchange agent (embedded in Codex vs. external service?).

## Next Steps
1. Define developer personas/use cases to anchor requirements.
2. Draft the `learnings.md` template and turn-level schema.
3. Prototype the Knowledge Exchange agent (capture + synthesis) on a single session.
4. Evaluate context injection interfaces so Codex can consume prior insights safely.
