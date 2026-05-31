# Feature Retrieval Index: MCP Terminal Server

## Retrieval Keywords

MCP terminal, terminal MCP, mcp_servers terminal, terminal tools, SSH MCP, tmux MCP, terminal session MCP, open_session, send_keys, run_command, terminal MCP server, mcp-to-skills terminal, lifecycle tmux, terminal operations

## Scope

- MCP server that exposes terminal and tmux operations as AI agent tools
- SSH session management via MCP
- tmux session lifecycle management for AI agents
- Excludes: web-based terminal UI (see `web-terminal-tmux-sessions.md`), MCP-to-skills bridge (separate)

## Main Behavior

- MCP server started as a standalone process, registered in agent MCP config
- Tools expose: open session, send keys, run command, kill session, list sessions, SSH connect
- Supports `lifecycle="tmux"` parameter for persistent background sessions
- Terminal and SSH helpers in `helpers.py`, `ssh.py`, `constants.py`

## Code Map

- `core/engine/mcp_servers/terminal/main.py` — MCP server entry point
- `core/engine/mcp_servers/terminal/terminal.py` — terminal tool logic
- `core/engine/mcp_servers/terminal/sessions.py` — session state management
- `core/engine/mcp_servers/terminal/operations.py` — terminal operations
- `core/engine/mcp_servers/terminal/ssh.py` — SSH session support
- `core/engine/mcp_servers/terminal/helpers.py` — helper utilities
- `core/engine/mcp_servers/terminal/constants.py` — constants
- `core/engine/mcp_servers/terminal/config.template.json` — MCP config template

## Search Commands

```bash
find core/engine/mcp_servers/terminal/ -type f
cat core/engine/mcp_servers/terminal/main.py | head -40
cat core/engine/mcp_servers/terminal/operations.py | head -40
```

## Related Features

- `core/features/web-terminal-tmux-sessions.md`
- `core/features/config-settings-mcp-skills.md`
- `core/features/agent-cli.md`

## Update Notes

- MCP server must be registered in agent config via `sync-mcp` or `config/mcp-servers` UI
- SSH private key paths configured in `settings.json5` under `services.terminal`
