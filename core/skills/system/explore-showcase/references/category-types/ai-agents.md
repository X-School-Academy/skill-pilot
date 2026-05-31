# Category: AI Agents — Types

Progressively deeper agent construction — from a single chatbot to a multi-agent workflow.

Primary audiences: AI agent builders, AI agent learners, job seekers.

## Types

### AG1. Single-prompt chatbot
- The minimum viable agent — one prompt, one tool, one loop.

### AG2. Tool-using agent
- An agent that calls a small set of tools (file read, HTTP, calculator).

### AG3. RAG agent
- Ingest a folder, build an index, answer with citations.

### AG4. Scheduled / background agent
- Runs on a cron or in a long-running loop via `schedule` / `loop` / `background-prompt`.

### AG5. Multi-agent workflow
- Compose agents into a workflow (planner → executor → reviewer) via `agent-workflow`.

### AG6. Remote-control agent (Discord, webhook)
- Trigger and approve agent runs remotely; human-in-the-loop approvals.

### AG7. Benchmark / comparison
- Run the same task across two models or two skill setups and produce a cost/latency report.
