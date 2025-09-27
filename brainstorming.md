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
- **Insight Engine**: Uses NLP/LLM prompts to tag gaps ("What is `useEffect`?"), confusion, successes, and follow-ups.
- **Artifact Store**: Persists structured logs, summaries, and action plans with versioning/access controls.
- **Review Console**: UI for timelines, key decisions, suggested learning, and reproducible playbooks.
- **Context Injector**: Supplies relevant past insights to Codex when a new session begins.

## Prototype: Sub-Agent Notebook
- Introduce a "notetaker" sub-agent sitting beside Codex.
- Each turn it records: what happened, where confusion appeared, and the takeaway for next time.
- Entries append to a human-readable `learnings.md`, using a consistent template (turn ID, action, gap, outcome).
- Periodic lightweight summaries keep the file digestible; older sessions archived on session end.
- Codex and the developer read the latest notes before the next session, aligning on gaps and focus areas.

## Integrity Discussion
- Merkle trees would offer tamper-proof, shareable proofs but add complexity (canonical serialization, hash storage, tooling).
- For the MVP, a simpler hash chain or plain version-controlled markdown is sufficient.
- Escalate to Merkle-backed logs only if auditability or selective proof-sharing becomes a requirement.

## Happy Path Walkthrough
1. **Session 1**: Coder + AI build a React site; notetaker captures each exchange and synthesizes a `learnings.md` entry (timeline, gaps, next reps).
2. **Between Sessions**: Notes are stored/versioned. Key findings include: needs more practice with hooks, deployment still theoretical.
3. **Session 2**: Coder reviews the latest entry and states goals ("review `useEffect`, practice Netlify deploy"). Codex receives the same context and tailors help accordingly.
4. **Execution**: Coder reimplements components with minimal prompting, deploys to Netlify, and closes remaining gaps.
5. **Wrap-Up**: Notetaker marks hooks gap resolved, records deployment success, and proposes next reps (e.g., automate build).

## Flow Overview
```
+----------------------+
| Start Session        |
+----------+-----------+
           |
           v
+----------------------+        +----------------------+
| Coder ↔ AI Exchange |<-------| Context from Previous |
| (solve current task) |        | learnings.md          |
+----------+-----------+        +----------------------+
           |
           v
+----------------------+
| Notetaker Captures   |
| turn details         |
+----------+-----------+
           |
           v
+----------------------+
| Session Ends         |
+----------+-----------+
           |
           v
+----------------------+
| Synthesize new       |
| learnings.md entry   |
+----------+-----------+
           |
           v
+----------------------+
| Store & Version Log  |
+----------+-----------+
           |
           v
+----------------------+
| Next Session Begins  |
+----------+-----------+
           |
           v
+----------------------+
| Review notes;        |
| adjust coaching      |
+----------+-----------+
           |
           v
+----------------------+
| Resume Exchange Loop |
+----------------------+
```

## Open Questions
- Exact schema for each turn (fields, tagging vocabulary, confidence scores?).
- How and when to trigger summaries vs. raw log entries.
- Privacy/governance requirements per organization; opt-in/export/delete flows.
- Tooling for the notetaker (runs client-side? server-side? plug-in to Codex?).

## Next Steps
1. Define developer personas/use cases to anchor requirements.
2. Draft the `learnings.md` template and turn-level schema.
3. Prototype the notetaker sub-agent (capture + synthesis) on a single session.
4. Evaluate context-injection interfaces so Codex can consume prior insights safely.
