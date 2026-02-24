# New UI Design

## Features

- Home screen at `/` with sidebar navigation and prompt input
- New Session: create tmux-backed AI agent sessions from the home screen
- Live Sessions at `/terminals`: list, connect, and close tmux sessions
- Terminal iframe with padding, auto-zoom, detach/kill controls
- Heartbeat-based session cleanup (10s timeout after browser close)
- Backend shutdown hook to clean up tmux sessions
- Course viewer at `/courses`
- Dev Swarm at `/dev-swarm`
- Processes view: read-only external tmux session viewer
- MCP Servers view: list, add, edit, delete MCP servers; sync skills button
- Placeholder views for remaining features (Learning, Projects, Research, Tasks, etc.)

## Docs

| File | Contents |
|------|----------|
| `requirement.md` | Original UI redesign requirements |
| `dev-plan.md` | Implementation plan for the initial UI redesign |
| `dev-summary.md` | Summary of the initial UI redesign |
| `terminal-session.md` | Terminal session management requirements |
| `terminal-session-dev-plan.md` | Dev plan with gap analysis and implementation phases |
| `terminal-session-summary.md` | Summary of terminal session changes |
| `mcp-servers.md` | MCP Servers management requirements |
| `mcp-servers-dev-plan.md` | MCP Servers dev plan |
| `mcp-servers-summary.md` | MCP Servers implementation summary |
