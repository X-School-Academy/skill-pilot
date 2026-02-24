# Discord Support Bot

## Features

- LLM-powered auto-reply Discord bot in the core engine (py-cord 2.6.1)
- Responds to all text channels and DMs
- Three-tier chat memory: running summary + recent buffer + JSONL cache
- 16K token budget with automatic summarisation of old messages
- Broadcast DM to all guild members via REST API
- Crash recovery from JSONL session files
- Runs alongside FastAPI server as a background async task
- WebUI: Discord Bot page with token setup form and session history tabs
- REST API endpoints for bot status, session listing, and token management

## Docs

| File | Contents |
|---|---|
| requirement.md | Requirements: bot behaviour, memory architecture, WebUI spec |
| dev-plan.md | Implementation plan, gap analysis, and confirmed design decisions |
| dev-summary.md | What was built, files changed, and design decisions |
| issues.md | Severity-ranked code review findings with impact and file references |
