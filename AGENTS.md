# Hack092725 Agent Playbook

## Why this exists
- Coding agents like Claude and Codex operate with guidance files (e.g., `Claude.md`).
- Hack092725 mirrors that idea for humans so we avoid redundant questions and learn from AI-assisted work.
- Use this document whenever you collaborate with the system so every session compounds prior knowledge.

## Core agent roles
### Knowledge Exchange (KE) Agent
- Retrieves past user documents and relevant context.
- Reprompts tasks based on what has already been learned.
- Synthesizes new insights from each session and writes them back to the knowledge base.

### Task Agent
- Executes the user-facing work and produces assistant messages.
- Accepts new instructions, appending them to the working context.
- Prompts the human for approval when reusing prior solutions.

## Session blueprint
### First pass (learning gaps discovery)
1. `<session>` starts.
2. User asks the initial question (e.g., “What is `useEffect` in React?”).
3. Task Agent executes the request and responds to the user.
4. KE Agent logs the user request to Documents.
5. System records a “user actions” entry.
6. KE Agent captures what was learned from user actions and documents it.
7. KE Agent logs the Task Agent’s output to Documents.
8. `</session>` closes the loop.

### Second pass (accelerated build with prior knowledge)
1. Session starts with **learn mode** toggled on.
2. User repeats the question (same React `useEffect` example).
3. KE Agent retrieves the previous documents.
4. KE Agent reprompts the task, leveraging the retrieved knowledge.
5. Task Agent summarizes the prior solution: “Here’s how we solved it last time—proceed?” (include the markdown snapshot from step 3).
6. User approves the proposed plan.
7. Task Agent executes the task.
8. KE Agent logs the user request to Documents again.
9. System records a new “user actions” entry.
10. KE Agent writes back what was learned from the user action plus documents.
11. KE Agent archives the Task Agent’s output in Documents.
12. Session ends.

## Document taxonomy
- `user actions`: timeline of what the human did or decided.
- `synthesized learnings`: distilled takeaways worth reusing.
- `agent actions`: what the automation executed.

## Implementation notes
- The OpenAI Agents SDK assigns and manages the session ID for every run—reuse it to stitch documents together.
- Keep “learn mode” off for discovery sessions, on for acceleration sessions.
- Ensure every loop produces fresh synthesized learnings so the system stays current.

## Human collaboration checklist
- Capture knowledge gaps explicitly during first-pass sessions.
- Before repeating a task, review (or ask the KE Agent to retrieve) prior documents.
- Confirm Task Agent plans when reusing prior work to avoid incorrect assumptions.
- Keep Documents tidy; they are the source of truth for future sessions.
